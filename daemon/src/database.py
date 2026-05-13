"""
Neo v2 — Database Schema
SQLModel tables for sessions, messages, tasks, and execution events.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from contextlib import contextmanager

from sqlmodel import SQLModel, Field, Session, create_engine


# --- Enums ---

class TaskPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    DELEGATING = "delegating"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"
    REJECTED = "rejected"


# --- Models ---

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = Field(default="New Chat")
    model: str = Field(default="gemini-2.5-flash")
    telegram_chat_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  # "albin", "neo", "system", "agent:<role>"
    content: str
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    prompt: str
    phase: str = Field(default=TaskPhase.IDLE)
    plan: Optional[str] = None
    agents_assigned: Optional[str] = None  # JSON list
    agent_output: Optional[str] = None
    review_output: Optional[str] = None
    final_summary: Optional[str] = None
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ExecutionEvent(SQLModel, table=True):
    __tablename__ = "execution_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    event_type: str  # "plan", "approve", "reject", "delegate", "execute", "review", "complete", "error"
    agent_role: Optional[str] = None
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryNode(SQLModel, table=True):
    __tablename__ = "memory_nodes"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    content: str
    node_type: str = Field(default="past_decision") # "architectural_rule", "past_decision", "project_fact"
    metadata_json: Optional[str] = None
    embedding_json: str  # JSON string of List[float]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    path: str
    is_indexed: bool = Field(default=False)
    last_indexed: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Engine ---

import os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "neo.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
