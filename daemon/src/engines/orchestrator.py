"""
Neo v2 — Orchestrator Engine
The core supervisor pipeline: planning, delegation, review, synthesis.
Implements the CTO-grade orchestration loop with approval gates.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable

from sqlmodel import Session as DBSession, select

from ..database import (
    engine, Task, TaskPhase, ChatMessage, ChatSession,
    ExecutionEvent, get_session
)
from .context import (
    get_workspace_context, gather_file_context, get_constitution,
    get_directory_tree, CLIENTLY_ROOT
)
from .openclaw import get_openclaw, RuntimeStatus
from .llm import call_gemini, _get_client
from .memory import memory_manager
from .broadcaster import global_broadcaster
from .mcp_manager import mcp_manager
from .skill_manager import skill_manager
from .tool_manager import tool_manager

# Initialize external integrations
mcp_manager.load_and_start()
skill_manager.scan_skills()


# --- System Prompts ---

NEO_SYSTEM = f"""You are Neo — the CTO of the Cliently engineering operation.
You provide strategic technical leadership to Albin.

{skill_manager.get_skill_descriptions()}

PROTOCOL:
- Address the user as "Albin". Maintain a professional, direct tone.
- No emojis. No informality. Respond as a senior technical executive.
- You are architecture-first. Prioritise security, consistency, and long-term integrity.
- You have full visibility into the Cliently project ecosystem.
- Format all output in clean GitHub-style Markdown.
- Do not repeat project summaries already provided in conversation history.
- Be concise. Be decisive. Be correct."""

NEO_PLANNER = """You are Neo in strategic planning mode.
Given Albin's request and the workspace context, generate a structured execution plan.

RESOURCES & CAPABILITIES:
- You have access to specialized MCP Tools (GitHub, Database, sequential-thinking, n8n, etc.).
- You have access to specialized Antigravity Skills (n8n, security-auditor, memory, etc.).
- Use the 'hire_specialized_agent' tool to delegate complex tasks to Skill-based agents.
- Roster: Backend Architect, Frontend Architect, Security Analyst, n8n Automation, Sequential Thinking, Memory Architect, Antigravity Agent.

OUTPUT FORMAT:
## Objective
[What needs to be accomplished]

## Affected Files
- [file path 1]
- [file path 2]

## Risks
- [risk 1]
- [risk 2]

## Execution Strategy
### Agent: [Role Name]
- Task: [specific task]
- Files: [files to inspect/modify]

## Success Criteria
- [criterion 1]
- [criterion 2]

## Estimated Impact
[Low/Medium/High] — [brief justification]"""

NEO_AGENT = """You are a specialist engineer working under Neo, the CTO.
Execute the assigned task with precision. Draft complete code, analysis, or documentation.

CAPABILITIES:
- You have access to MCP Tools and Antigravity Skills.
- Execute tools to perform actions in the workspace, query the database, or manage GitHub.
- Use the 'hire_specialized_agent' tool for tasks requiring high-level specialized skills.

Be exhaustive but structured. Use Markdown formatting. Maintain the highest standards."""

NEO_REVIEWER = """You are Neo performing a supervisory review.
Critically evaluate the agent's work for:
1. Technical accuracy
2. Security implications
3. Architecture compliance
4. Code quality
5. Completeness

Deliver a structured executive summary to Albin with:
1. **Executive Overview**
2. **Key Findings**
3. **Issues & Risks**
4. **Recommendations**
5. **Next Steps**

Be direct. Be professional. Address Albin."""


# --- Timeline Logging ---

def log_event(task_id: str, event_type: str, detail: str, agent_role: str = None):
    """Record an execution event in the timeline."""
    with get_session() as db:
        event = ExecutionEvent(
            task_id=task_id,
            event_type=event_type,
            agent_role=agent_role,
            detail=detail,
        )
        db.add(event)
        db.commit()


def save_message(session_id: str, role: str, content: str, metadata_json: str = None, broadcast: bool = True):
    """Save a chat message to the database and optionally broadcast it."""
    with get_session() as db:
        # Update session timestamp
        session = db.get(ChatSession, session_id)
        if session:
            session.updated_at = datetime.now(timezone.utc)
            if role == "albin" and session.title == "New Chat":
                session.title = content[:35] + ("..." if len(content) > 35 else "")
            db.add(session)

        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        db.add(msg)
        db.commit()
    
    if broadcast:
        asyncio.create_task(global_broadcaster.broadcast(session_id, {
            "type": "message",
            "role": role,
            "content": content,
            "metadata_json": metadata_json,
            "created_at": datetime.now(timezone.utc).isoformat()
        }))


# --- Orchestration Pipeline ---

async def handle_chat(
    session_id: str,
    prompt: str,
    model: str,
    broadcast: Optional[Callable[[str, dict], Awaitable[None]]] = None,
    metadata: Optional[dict] = None,
) -> str:
    # Use global_broadcaster if none provided
    broadcast = broadcast or global_broadcaster.broadcast
    """
    Main entry point for all user messages.
    Determines whether to respond directly or trigger the supervisor pipeline.
    """
    # Save and broadcast user prompt immediately
    meta_json = json.dumps(metadata) if metadata else None
    save_message(session_id, "albin", prompt, metadata_json=meta_json, broadcast=True)

    # Quick commands
    if prompt.strip().lower() in ["/status", "git status"]:
        from .context import get_git_status
        status = get_git_status()
        reply = f"**Git Status:**\n```\n{status}\n```"
        save_message(session_id, "neo", reply, broadcast=True)
        return reply

    # Detect if this needs the full supervisor pipeline
    needs_pipeline = _needs_deep_work(prompt)

    if needs_pipeline and _get_client():
        # Create task and start pipeline
        task = _create_task(session_id, prompt)
        asyncio.create_task(
            _run_pipeline(task.id, session_id, prompt, model, broadcast)
        )
        ack = "Acknowledged, Albin. Initiating the supervisor pipeline. I will present an execution plan for your approval before proceeding."
        save_message(session_id, "neo", ack, broadcast=True)
        return ack

    # Direct conversational response
    if _get_client():
        history = _get_chat_history(session_id, limit=12)
        context = get_workspace_context()
        constitution = get_constitution()
        
        # Query CTO memory (Architectural Rules & Past Decisions)
        arch_rules = memory_manager.query_memory(prompt, top_k=3, node_type="architectural_rule")
        past_decisions = memory_manager.query_memory(prompt, top_k=3, node_type="past_decision")
        
        memory_context = ""
        if arch_rules:
            memory_context += "\n--- CTO ARCHITECTURAL RULES ---\n"
            for mem in arch_rules:
                memory_context += f"- {mem['content']}\n"
        
        if past_decisions:
            memory_context += "\n--- RELEVANT PAST DECISIONS ---\n"
            for mem in past_decisions:
                memory_context += f"- Decision (at {mem.get('created_at', 'unknown')}): {mem['content']}\n"

        full_prompt = f"""--- WORKSPACE ---
{context}

--- CONSTITUTION ---
{constitution[:2000]}
{memory_context}
--- CONVERSATION HISTORY ---
{history}

--- ALBIN'S CURRENT REQUEST ---
{prompt}

Respond directly to Albin's latest request. Do not repeat information already in the conversation.
Maintain your persona as the Cliently CTO. Be architecture-first. If relevant, reference past decisions or architectural rules from your memory."""

        tools = tool_manager.get_all_tools()
        reply = call_gemini(
            full_prompt, NEO_SYSTEM, model=model, 
            temperature=0.3, tools=tools, tool_handler=tool_manager
        )
        save_message(session_id, "neo", reply, broadcast=True)
        
        # Store non-trivial conversation into memory with better formatting
        if len(prompt) > 20 or len(reply) > 100:
            memory_manager.add_memory(
                content=f"DECISION/INTERACTION: Albin asked '{prompt}'. Neo responded with architectural guidance focusing on {reply[:200]}...",
                meta={
                    "type": "chat_decision",
                    "session": session_id,
                    "prompt_summary": prompt[:100],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
        return reply

    fallback = f"Received: '{prompt}' — GEMINI_API_KEY not configured."
    save_message(session_id, "neo", fallback)
    return fallback


async def _run_pipeline(
    task_id: str,
    session_id: str,
    prompt: str,
    model: str,
    broadcast: Optional[Callable[[str, dict], Awaitable[None]]] = None,
):
    # Use global_broadcaster if none provided
    broadcast = broadcast or global_broadcaster.broadcast
    """
    The full CTO supervisor pipeline:
    1. Strategic Planning
    2. Task Contract → Approval Gate
    3. Agent Delegation
    4. Review & Synthesis
    5. Executive Summary
    """
    try:
        # --- Phase 1: Strategic Planning ---
        _update_task_phase(task_id, TaskPhase.PLANNING)
        await broadcast(session_id, {"type": "phase", "phase": "planning"})
        log_event(task_id, "plan", "Analyzing request and gathering context.")

        context = get_workspace_context()
        file_context = gather_file_context(prompt)
        constitution = get_constitution()
        tree = get_directory_tree(CLIENTLY_ROOT, depth=2)

        # Query CTO memory for past context
        arch_rules = memory_manager.query_memory(prompt, top_k=5, node_type="architectural_rule")
        past_decisions = memory_manager.query_memory(prompt, top_k=5, node_type="past_decision")

        memory_context = ""
        if arch_rules:
            memory_context += "\n--- MANDATORY ARCHITECTURAL RULES ---\n"
            for mem in arch_rules:
                memory_context += f"- RULE: {mem['content']}\n"
        
        if past_decisions:
            memory_context += "\n--- RELEVANT PAST DECISIONS ---\n"
            for mem in past_decisions:
                memory_context += f"- PAST DECISION: {mem['content']}\n"

        plan_prompt = f"""Albin asked: "{prompt}"

--- WORKSPACE ---
{context}

--- DIRECTORY STRUCTURE ---
{tree}

--- FILE CONTEXT ---
{file_context[:8000]}

--- CONSTITUTION ---
{constitution[:2000]}
{memory_context}
Create a precise, structured execution plan following the output format exactly.
Consider any relevant past decisions or architectural rules mentioned above to ensure consistency."""

        tools = tool_manager.get_all_tools()
        plan = call_gemini(
            plan_prompt, NEO_PLANNER, model=model, 
            temperature=0.1, tools=tools, tool_handler=tool_manager
        )
        _update_task(task_id, plan=plan)
        log_event(task_id, "plan", "Execution plan generated.")

        # --- Phase 2: Approval Gate ---
        _update_task_phase(task_id, TaskPhase.AWAITING_APPROVAL)
        await broadcast(session_id, {"type": "phase", "phase": "awaiting_approval"})

        # Build the approval card
        approval_card = {
            "type": "approval_card",
            "task_id": task_id,
            "plan": plan,
        }
        save_message(session_id, "neo", plan, metadata_json=json.dumps(approval_card))
        await broadcast(session_id, {
            "type": "approval_request",
            "task_id": task_id,
            "plan": plan,
        })
        log_event(task_id, "approve", "Awaiting Albin's approval.")

        # Wait for approval (poll the task state)
        approved = await _wait_for_approval(task_id, timeout=300)
        if not approved:
            _update_task_phase(task_id, TaskPhase.REJECTED)
            log_event(task_id, "reject", "Task rejected or timed out.")
            msg = "Task cancelled. Standing by for your next directive, Albin."
            save_message(session_id, "neo", msg)
            await broadcast(session_id, {"type": "phase", "phase": "rejected"})
            return

        log_event(task_id, "approve", "Approved by Albin. Proceeding.")

        # --- Phase 3: Agent Delegation ---
        _update_task_phase(task_id, TaskPhase.DELEGATING)
        await broadcast(session_id, {"type": "phase", "phase": "delegating"})
        log_event(task_id, "delegate", "Assigning specialized agents.")

        # Determine agent roles from the plan
        roles = _determine_agent_roles(plan)
        _update_task(task_id, agents_assigned=json.dumps(roles))

        # Check OpenClaw runtime availability
        openclaw = get_openclaw()
        runtime_state = await openclaw.check_health()
        runtime_available = runtime_state.status == RuntimeStatus.CONNECTED

        if runtime_available:
            msg = "Approved. Dispatching via OpenClaw runtime:\n" + "\n".join(f"- **{r}**" for r in roles)
        else:
            msg = "Approved. OpenClaw offline — executing via direct agents:\n" + "\n".join(f"- **{r}**" for r in roles)
        save_message(session_id, "neo", msg)
        await broadcast(session_id, {"type": "message", "role": "neo", "content": msg})
        await broadcast(session_id, {"type": "runtime_status", "connected": runtime_available})

        # --- Phase 4: Execution ---
        _update_task_phase(task_id, TaskPhase.EXECUTING)
        await broadcast(session_id, {"type": "phase", "phase": "executing"})

        # Try OpenClaw dispatch first
        if runtime_available:
            log_event(task_id, "execute", "Dispatching to OpenClaw runtime.")
            dispatch = await openclaw.dispatch_task(
                task_id=task_id,
                plan=plan,
                context=context,
                prompt=prompt,
                agent_roles=roles,
            )
            if dispatch.success:
                log_event(task_id, "execute", f"OpenClaw accepted task: {dispatch.task_ref}")
                # Poll for completion
                combined = await _poll_openclaw_task(task_id, dispatch.task_ref, session_id, broadcast)
                if combined:
                    _update_task(task_id, agent_output=combined)
                else:
                    # OpenClaw execution failed — fall through to direct execution
                    log_event(task_id, "execute", "OpenClaw execution failed. Falling back to direct agents.")
                    runtime_available = False
            else:
                log_event(task_id, "execute", f"OpenClaw dispatch failed: {dispatch.error}. Falling back.")
                runtime_available = False

        # Fallback: Direct agent execution via Gemini
        if not runtime_available:
            async def run_agent(role: str) -> str:
                log_event(task_id, "execute", f"{role} starting analysis.", agent_role=role)
                await broadcast(session_id, {"type": "agent_status", "agent": role, "status": "working"})

                # Antigravity Agent — write bridge directive for external pickup
                if role == "Antigravity Agent":
                    bridge_path = os.path.join(CLIENTLY_ROOT, ".antigravity_bridge.md")
                    with open(bridge_path, "w", encoding="utf-8") as f:
                        f.write(f"# NEO TECHNICAL DIRECTIVE\n\n## Plan\n{plan}\n\n## Context\n{context[:2000]}\n\n## Request\n{prompt}\n\n## Files\n{file_context[:3000]}")
                    log_event(task_id, "execute", "Directive passed to Antigravity.", agent_role=role)
                    return f"### {role}\nExecution delegated to external Antigravity environment."

                agent_prompt = f"""--- ROLE: {role} ---

--- NEO'S EXECUTION PLAN ---
{plan}

--- WORKSPACE ---
{context}

--- FILE CONTEXT ---
{file_context[:6000]}

--- INSTRUCTIONS ---
Execute your assigned portion of the plan. Address: "{prompt}"
Be thorough, technical, and precise."""

                tools = tool_manager.get_all_tools()
                output = call_gemini(
                    agent_prompt, NEO_AGENT, model=model, 
                    temperature=0.2, tools=tools, tool_handler=tool_manager
                )
                log_event(task_id, "execute", f"{role} completed.", agent_role=role)
                await broadcast(session_id, {"type": "agent_status", "agent": role, "status": "done"})
                return f"### {role}\n\n{output}"

            results = await asyncio.gather(*[run_agent(r) for r in roles])
            combined = "\n\n---\n\n".join(results)
            _update_task(task_id, agent_output=combined)

        # --- Phase 5: Review ---
        _update_task_phase(task_id, TaskPhase.REVIEWING)
        await broadcast(session_id, {"type": "phase", "phase": "reviewing"})
        log_event(task_id, "review", "Synthesizing agent reports.")

        review_prompt = f"""Albin asked: "{prompt}"

--- AGENT REPORTS ---
{combined[:20000]}

--- INSTRUCTIONS ---
Review all findings. Deliver a polished executive summary to Albin.
Address discrepancies. Ensure architectural integrity.
Follow the review output format precisely."""

        final = call_gemini(review_prompt, NEO_REVIEWER, model=model, temperature=0.1)
        _update_task(task_id, review_output=final, final_summary=final)
        log_event(task_id, "review", "Executive summary generated.")

        # --- Phase 6: Complete ---
        _update_task_phase(task_id, TaskPhase.COMPLETE)
        with get_session() as db:
            task = db.get(Task, task_id)
            if task:
                task.completed_at = datetime.now(timezone.utc)
                db.add(task)
                db.commit()

        save_message(session_id, "neo", final)
        
        # Save pipeline result to CTO Memory
        memory_manager.add_memory(
            content=f"Task executed for: {prompt}\nSummary:\n{final}",
            meta={"type": "pipeline", "task_id": task_id, "session": session_id}
        )
        
        await broadcast(session_id, {"type": "phase", "phase": "complete"})
        await broadcast(session_id, {"type": "message", "role": "neo", "content": final})
        log_event(task_id, "complete", "Pipeline complete.")

        # --- Phase 7: CTO Reflection & Knowledge Consolidation ---
        asyncio.create_task(_reflect_on_task(task_id, session_id, prompt, combined, final, model))

    except Exception as e:
        _update_task_phase(task_id, TaskPhase.FAILED)
        log_event(task_id, "error", str(e))
        msg = f"Pipeline error: {str(e)}"
        save_message(session_id, "neo", msg)
        await broadcast(session_id, {"type": "phase", "phase": "failed"})
        import traceback
        traceback.print_exc()


# --- Approval Flow ---

async def _wait_for_approval(task_id: str, timeout: int = 300) -> bool:
    """Poll the task phase until it leaves AWAITING_APPROVAL."""
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(1.5)
        elapsed += 1.5
        with get_session() as db:
            task = db.get(Task, task_id)
            if not task:
                return False
            if task.phase == TaskPhase.DELEGATING:
                return True  # Approved
            if task.phase in [TaskPhase.REJECTED, TaskPhase.FAILED]:
                return False
    return False


def approve_task(task_id: str) -> bool:
    """Approve a task — moves it from AWAITING_APPROVAL to DELEGATING."""
    with get_session() as db:
        task = db.get(Task, task_id)
        if not task or task.phase != TaskPhase.AWAITING_APPROVAL:
            return False
        task.phase = TaskPhase.DELEGATING
        db.add(task)
        db.commit()
        log_event(task_id, "approve", "Approved by Albin.")
        return True


def reject_task(task_id: str) -> bool:
    """Reject a task."""
    with get_session() as db:
        task = db.get(Task, task_id)
        if not task or task.phase != TaskPhase.AWAITING_APPROVAL:
            return False
        task.phase = TaskPhase.REJECTED
        db.add(task)
        db.commit()
        log_event(task_id, "reject", "Rejected by Albin.")
        return True


# --- Helpers ---

def _needs_deep_work(prompt: str) -> bool:
    """Detect whether a prompt requires the full supervisor pipeline."""
    keywords = [
        "review", "audit", "analyze", "scan", "report", "investigate",
        "check", "inspect", "/hire", "/dispatch", "comprehensive",
        "refactor", "implement", "fix", "build", "create", "deploy",
        "security", "performance", "architecture", "migrate",
    ]
    lower = prompt.lower()
    return any(kw in lower for kw in keywords)


def _create_task(session_id: str, prompt: str) -> Task:
    """Create a new task record."""
    with get_session() as db:
        task = Task(session_id=session_id, prompt=prompt, phase=TaskPhase.PLANNING)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


def _update_task_phase(task_id: str, phase: TaskPhase):
    with get_session() as db:
        task = db.get(Task, task_id)
        if task:
            task.phase = phase
            db.add(task)
            db.commit()


def _update_task(task_id: str, **kwargs):
    with get_session() as db:
        task = db.get(Task, task_id)
        if task:
            for k, v in kwargs.items():
                setattr(task, k, v)
            db.add(task)
            db.commit()


def _determine_agent_roles(plan: str) -> list[str]:
    """Parse the plan to determine which agent roles to dispatch."""
    plan_lower = plan.lower()
    roles = []

    if any(kw in plan_lower for kw in ["api", "database", "backend", "prisma", "migration"]):
        roles.append("Backend Architect")
    if any(kw in plan_lower for kw in ["ui", "frontend", "component", "css", "react", "swiftui"]):
        roles.append("Frontend Architect")
    if any(kw in plan_lower for kw in ["security", "auth", "rls", "vulnerability", "secrets"]):
        roles.append("Security Analyst")
    if any(kw in plan_lower for kw in ["test", "qa", "regression", "validation"]):
        roles.append("QA Engineer")
    if any(kw in plan_lower for kw in ["performance", "optimize", "profiling", "bottleneck"]):
        roles.append("Performance Analyst")
    if any(kw in plan_lower for kw in ["fix", "implement", "modify", "refactor", "create file", "build", "coding", "code"]):
        roles.append("Antigravity Agent")
    if any(kw in plan_lower for kw in ["workflow", "automation", "n8n", "external integration", "webhook"]):
        roles.append("n8n Automation")
    if any(kw in plan_lower for kw in ["memory", "graphify", "knowledge", "persistent context", "long-term"]):
        roles.append("Memory Architect")
    if any(kw in plan_lower for kw in ["think", "logic", "reasoning", "complex problem", "branching"]):
        roles.append("Sequential Thinking")

    if not roles:
        roles.append("Technical Analyst")

    return roles


def _get_chat_history(session_id: str, limit: int = 12) -> str:
    """Get recent chat history formatted for AI context."""
    with get_session() as db:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        msgs = db.exec(stmt).all()
        lines = [f"{m.role}: {m.content}" for m in reversed(msgs)]
        return "\n".join(lines)


def get_active_task(session_id: str) -> Optional[Task]:
    """Get the active (non-terminal) task for a session."""
    terminal = [TaskPhase.COMPLETE, TaskPhase.FAILED, TaskPhase.REJECTED, TaskPhase.IDLE]
    with get_session() as db:
        stmt = (
            select(Task)
            .where(Task.session_id == session_id)
            .order_by(Task.created_at.desc())
            .limit(1)
        )
        task = db.exec(stmt).first()
        if task and task.phase not in terminal:
            return task
        return None


def get_task_timeline(task_id: str) -> list[dict]:
    """Get the execution timeline for a task."""
    with get_session() as db:
        stmt = (
            select(ExecutionEvent)
            .where(ExecutionEvent.task_id == task_id)
            .order_by(ExecutionEvent.created_at)
        )
        events = db.exec(stmt).all()
        return [
            {
                "event_type": e.event_type,
                "agent_role": e.agent_role,
                "detail": e.detail,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]


async def _poll_openclaw_task(
    task_id: str,
    task_ref: str,
    session_id: str,
    broadcast: Callable[[str, dict], Awaitable[None]],
    timeout: int = 600,
    interval: float = 3.0,
) -> Optional[str]:
    """
    Poll OpenClaw for task completion.
    Returns the combined agent output, or None if execution failed.
    """
    openclaw = get_openclaw()
    elapsed = 0.0

    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval

        status = await openclaw.get_task_status(task_ref)
        current = status.get("status", "unknown")

        await broadcast(session_id, {
            "type": "openclaw_progress",
            "task_ref": task_ref,
            "status": current,
            "elapsed": int(elapsed),
        })

        if current == "complete":
            result = await openclaw.get_task_result(task_ref)
            log_event(task_id, "execute", f"OpenClaw task completed after {int(elapsed)}s.")
            return result or "Execution completed — no output returned."

        if current in ("failed", "error"):
            log_event(task_id, "error", f"OpenClaw task failed: {status.get('error', 'unknown')}")
            return None

    log_event(task_id, "error", f"OpenClaw task timed out after {timeout}s.")
    return None


async def _reflect_on_task(task_id: str, session_id: str, prompt: str, execution_output: str, summary: str, model: str):
    """
    Neo reflects on the completed task to extract long-term architectural knowledge.
    This is what makes him a 'CTO' — he learns from every operation.
    """
    try:
        reflection_prompt = f"""You are the Cliently CTO. You just completed a technical task for Albin.
--- TASK ---
Prompt: {prompt}
Summary of Results: {summary}

--- EXECUTION DATA (TRUNCATED) ---
{execution_output[:5000]}

--- INSTRUCTIONS ---
Reflect on this task. Extract any:
1. **Architectural Decisions**: Choices made about the stack, patterns, or structure.
2. **Lessons Learned**: Things that were difficult, unexpected, or should be remembered for next time.
3. **New Rules**: Any technical constraints or 'gold standards' that should apply to future work.

FORMAT:
Provide a list of concise 'Memory Nodes'. Each node should be a single self-contained technical statement.
Example: "We decided to use FastAPI for all internal microservices to ensure consistency with the daemon."
"""
        reflection = call_gemini(reflection_prompt, NEO_SYSTEM, model=model, temperature=0.2)
        
        # Parse and store nodes
        lines = reflection.split("\n")
        nodes_added = 0
        for line in lines:
            line = line.strip()
            if line and (line.startswith("- ") or line[0].isdigit() and line[1] == "."):
                content = line.lstrip("- 0123456789. ")
                if len(content) > 30:
                    memory_manager.add_memory(
                        content=content,
                        node_type="past_decision" if "decided" in content.lower() else "architectural_rule",
                        meta={"task_id": task_id, "session": session_id, "source": "reflection"}
                    )
                    nodes_added += 1
        
        logger.info(f"CTO Reflection complete for task {task_id}. Added {nodes_added} knowledge nodes.")
    except Exception as e:
        logger.error(f"Failed to reflect on task {task_id}: {e}")

