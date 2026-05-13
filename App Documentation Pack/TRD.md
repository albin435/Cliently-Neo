# Neo — Technical Requirements Document

# Stack

## Frontend
- SwiftUI
- Tuist
- Native macOS application

## Backend
- Python 3.13
- FastAPI daemon
- WebSocket communication

## Database
- SQLite
- ChromaDB/LanceDB for vector memory

## AI Providers
- Gemini 2.5 Pro
- Gemini 2.5 Flash

## Agent Bridge
- `.antigravity_bridge.md`

---

# Core Services

## Orchestrator Engine
Responsible for:
- planning
- delegation
- task supervision
- approval flow
- synthesis

## Memory Engine
Responsible for:
- persistent memory
- vector retrieval
- historical decision tracking
- project constitution loading

## Context Engine
Responsible for:
- repository scanning
- git analysis
- config parsing
- workspace indexing

## Execution Engine
Responsible for:
- task dispatching
- Antigravity bridge communication
- execution tracking
- retry logic

## Review Engine
Responsible for:
- architecture validation
- code review
- hallucination detection
- standards enforcement

---

# System Requirements

## Functional
- Full filesystem access
- Terminal execution support
- Git integration
- Persistent chat storage
- Multiple chat sessions
- Multi-model support
- Approval-based execution

## Non Functional
- low latency
- resilient orchestration
- replayable execution history
- local-first operation
- high reliability

---

# APIs

## FastAPI Endpoints

### /chat
Send user messages

### /task/create
Create task specifications

### /task/approve
Approve execution

### /task/reject
Reject execution

### /timeline
Retrieve execution history

### /memory/search
Semantic memory retrieval

---

# Security Model

- local-first architecture
- no cloud dependency required
- encrypted API key storage
- approval-required destructive actions

---

# Risks

- recursive orchestration loops
- context fragmentation
- token explosion
- hallucinated architectural decisions

Mitigation:
- supervisor checkpoints
- execution limits
- constitutional governance