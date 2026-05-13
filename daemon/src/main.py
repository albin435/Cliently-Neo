"""
Neo v2 — Main Server
FastAPI daemon with WebSocket real-time communication.
All endpoints serve the SwiftUI frontend.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import Session as DBSession, select

from .database import (
    init_db, engine, get_session,
    ChatSession, ChatMessage, Task, TaskPhase, ExecutionEvent,
    Workspace, MemoryNode
)
from .engines.indexer import repo_indexer
from .engines.orchestrator import (
    handle_chat, approve_task, reject_task,
    get_active_task, get_task_timeline, save_message,
)
from .engines.context import (
    get_workspace_context, get_git_status, get_git_branch,
    list_antigravity_skills, list_mcp_servers,
)
from .engines.openclaw import get_openclaw
from .engines.telegram_bot import telegram_bot
from .engines.broadcaster import global_broadcaster
from .engines.mcp_manager import mcp_manager
from .engines.skill_manager import skill_manager

# env is now loaded in engines/llm.py


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    # Start engines (non-blocking to prevent startup hang)
    asyncio.create_task(asyncio.to_thread(mcp_manager.load_and_start))
    asyncio.create_task(asyncio.to_thread(skill_manager.scan_skills))
    
    # Attempt initial OpenClaw connection check
    openclaw = get_openclaw()
    asyncio.create_task(openclaw.check_health())

    # Register listeners for unified broadcasting
    global_broadcaster.register(manager.broadcast)
    global_broadcaster.register(telegram_bot.broadcast)

    # Start Telegram bot
    asyncio.create_task(telegram_bot.start_bot())
    yield
    # Cleanup
    await openclaw.close()
    await telegram_bot.stop_bot()
    mcp_manager.stop_all()


app = FastAPI(title="Neo Daemon", version="2.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response


# --- WebSocket Manager ---

class ConnectionManager:
    """Manages WebSocket connections per session."""
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self.connections:
            self.connections[session_id] = set()
        self.connections[session_id].add(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self.connections:
            self.connections[session_id].discard(ws)
            if not self.connections[session_id]:
                del self.connections[session_id]

    async def broadcast(self, session_id: str, data: dict):
        if session_id in self.connections:
            dead = []
            for ws in self.connections[session_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections[session_id].discard(ws)


manager = ConnectionManager()


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    session_id: str
    prompt: str
    model: str = "gemini-2.5-flash"

class ChatResponse(BaseModel):
    response: str
    task_id: str | None = None
    task_phase: str | None = None

class TaskAction(BaseModel):
    task_id: str

class SessionResponse(BaseModel):
    id: str
    title: str
    model: str
    telegram_chat_id: str | None = None
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    metadata_json: str | None
    created_at: str

class WorkspaceRequest(BaseModel):
    name: str
    path: str


# --- Health ---

@app.get("/health")
async def health():
    from .engines.orchestrator import _get_client
    openclaw = get_openclaw()
    runtime = await openclaw.check_health()
    return {
        "status": "ok",
        "service": "Neo Daemon v2",
        "ai_ready": _get_client() is not None,
        "branch": get_git_branch(),
        "runtime": openclaw.get_status_dict(),
    }


# --- Sessions ---

@app.get("/sessions")
def list_sessions():
    with get_session() as db:
        stmt = select(ChatSession).order_by(ChatSession.updated_at.desc())
        results = db.exec(stmt).all()
        return [
            SessionResponse(
                id=s.id, title=s.title, model=s.model,
                telegram_chat_id=s.telegram_chat_id,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in results
        ]


@app.post("/sessions")
def create_session(model: str = "gemini-2.5-flash"):
    with get_session() as db:
        s = ChatSession(model=model)
        db.add(s)
        db.commit()
        db.refresh(s)
        return SessionResponse(
            id=s.id, title=s.title, model=s.model,
            telegram_chat_id=s.telegram_chat_id,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    with get_session() as db:
        s = db.get(ChatSession, session_id)
        if not s:
            raise HTTPException(404, "Session not found")
        # Delete messages and tasks
        msgs = db.exec(select(ChatMessage).where(ChatMessage.session_id == session_id)).all()
        for m in msgs:
            db.delete(m)
        tasks = db.exec(select(Task).where(Task.session_id == session_id)).all()
        for t in tasks:
            events = db.exec(select(ExecutionEvent).where(ExecutionEvent.task_id == t.id)).all()
            for e in events:
                db.delete(e)
            db.delete(t)
        db.delete(s)
        db.commit()
        return {"ok": True}


# --- Messages ---

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    with get_session() as db:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        results = db.exec(stmt).all()
        return [
            MessageResponse(
                id=r.id, session_id=r.session_id, role=r.role,
                content=r.content, metadata_json=r.metadata_json,
                created_at=r.created_at.isoformat(),
            )
            for r in results
        ]


# --- Chat ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(400, "Empty prompt.")

    # Check for active task blocking input
    active = get_active_task(req.session_id)
    if active and active.phase not in [TaskPhase.AWAITING_APPROVAL]:
        return ChatResponse(
            response=f"A task is in progress ({active.phase}). Please wait.",
            task_id=active.id,
            task_phase=active.phase,
        )

    reply = await handle_chat(
        session_id=req.session_id,
        prompt=prompt,
        model=req.model,
        broadcast=global_broadcaster.broadcast,
    )

    # Check if a task was created
    new_active = get_active_task(req.session_id)
    return ChatResponse(
        response=reply,
        task_id=new_active.id if new_active else None,
        task_phase=new_active.phase if new_active else None,
    )


# --- Task Actions ---

@app.post("/task/approve")
async def approve_task_endpoint(action: TaskAction):
    ok = approve_task(action.task_id)
    if not ok:
        raise HTTPException(400, "Cannot approve task — invalid state.")
    # Get session_id for the task to broadcast
    with get_session() as db:
        task = db.get(Task, action.task_id)
        if task:
            await global_broadcaster.broadcast(task.session_id, {"type": "phase", "phase": "delegating"})
    return {"ok": True}


@app.post("/task/reject")
async def reject_task_endpoint(action: TaskAction):
    ok = reject_task(action.task_id)
    if not ok:
        raise HTTPException(400, "Cannot reject task — invalid state.")
    with get_session() as db:
        task = db.get(Task, action.task_id)
        if task:
            save_message(task.session_id, "neo", "Understood. Task cancelled.")
            await global_broadcaster.broadcast(task.session_id, {"type": "phase", "phase": "rejected"})
    return {"ok": True}


@app.get("/task/status")
def task_status(session_id: str):
    active = get_active_task(session_id)
    if not active:
        return {"active": False, "phase": "idle", "task_id": None}
    return {
        "active": True,
        "phase": active.phase,
        "task_id": active.id,
    }


@app.get("/task/{task_id}/timeline")
def task_timeline(task_id: str):
    return get_task_timeline(task_id)


# --- Context & State ---

@app.get("/context")
async def get_context():
    openclaw = get_openclaw()
    runtime = await openclaw.check_health()
    return {
        "workspace": get_workspace_context(),
        "skills": list_antigravity_skills(),
        "mcps": list_mcp_servers(),
        "branch": get_git_branch(),
        "git_status": get_git_status(),
        "runtime": openclaw.get_status_dict(),
    }


@app.get("/tasks")
def list_tasks(limit: int = 50):
    """List execution history."""
    with get_session() as db:
        stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
        results = db.exec(stmt).all()
        return [
            {
                "id": t.id,
                "session_id": t.session_id,
                "prompt": t.prompt,
                "phase": t.phase,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in results
        ]


@app.get("/memory")
def list_memory(q: str | None = None, limit: int = 50):
    """List or search memory bank."""
    if q:
        from .engines.memory import memory_manager
        return memory_manager.query_memory(q, top_k=limit)
    
    with get_session() as db:
        stmt = select(MemoryNode).order_by(MemoryNode.created_at.desc()).limit(limit)
        results = db.exec(stmt).all()
        return [
            {
                "id": m.id,
                "content": m.content,
                "metadata": json.loads(m.metadata_json) if m.metadata_json else {},
                "created_at": m.created_at.isoformat(),
            }
            for m in results
        ]


# --- Workspaces ---

@app.get("/workspaces")
def list_workspaces():
    with get_session() as db:
        stmt = select(Workspace).order_by(Workspace.created_at.desc())
        results = db.exec(stmt).all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "path": w.path,
                "is_indexed": w.is_indexed,
                "last_indexed": w.last_indexed.isoformat() if w.last_indexed else None,
                "created_at": w.created_at.isoformat(),
            }
            for w in results
        ]


@app.post("/workspaces")
def create_workspace(req: WorkspaceRequest):
    with get_session() as db:
        w = Workspace(name=req.name, path=req.path)
        db.add(w)
        db.commit()
        db.refresh(w)
        return w


@app.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str):
    with get_session() as db:
        w = db.get(Workspace, workspace_id)
        if not w:
            raise HTTPException(404, "Workspace not found")
        db.delete(w)
        db.commit()
        return {"ok": True}


@app.post("/workspaces/{workspace_id}/index")
async def index_workspace_endpoint(workspace_id: str):
    with get_session() as db:
        w = db.get(Workspace, workspace_id)
        if not w:
            raise HTTPException(404, "Workspace not found")
        
        if repo_indexer.is_indexing:
            return {"status": "already_indexing", "progress": repo_indexer.progress}
        
        # Start async indexing
        asyncio.create_task(_run_indexing(workspace_id, w.path))
        return {"status": "started"}


@app.get("/workspaces/index/status")
def indexing_status():
    return {
        "is_indexing": repo_indexer.is_indexing,
        "progress": repo_indexer.progress,
        "current_file": repo_indexer.current_file,
        "total_files": repo_indexer.total_files,
    }


async def _run_indexing(workspace_id: str, path: str):
    await repo_indexer.index_repository(path)
    with get_session() as db:
        w = db.get(Workspace, workspace_id)
        if w:
            w.is_indexed = True
            w.last_indexed = datetime.now(timezone.utc)
            db.add(w)
            db.commit()


# --- Runtime (OpenClaw) ---

@app.get("/runtime/health")
async def runtime_health():
    """Check OpenClaw runtime connectivity."""
    openclaw = get_openclaw()
    await openclaw.check_health()
    return openclaw.get_status_dict()


@app.get("/runtime/status")
async def runtime_status():
    """Detailed runtime status with last known state."""
    openclaw = get_openclaw()
    return {
        **openclaw.get_status_dict(),
        "host": openclaw.state.host,
        "policy": {
            "auto_install": False,
            "auto_configure": False,
            "managed_by": "Albin (manual)",
            "sandbox": "Docker (local)",
        },
    }


# --- WebSocket ---

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await manager.connect(session_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can send pings or commands via WS
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(session_id, ws)


# --- Entry ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

@app.get("/test_broadcast")
async def test_broadcast_endpoint(session_id: str):
    await global_broadcaster.broadcast(session_id, {"type": "message", "role": "neo", "content": "Testing broadcast from daemon!"})
    return {"ok": True}

