# Neo — System Architecture

# High-Level Architecture

User
↓
Neo SwiftUI Client
↓
Neo Orchestrator Daemon
↓
OpenClaw Runtime
↓
Antigravity Execution Layer
↓
Filesystem / Tools / Terminal

---

# Frontend

## Neo macOS App
Built with:
- SwiftUI
- Tuist

Features:
- internal messaging workspace
- persistent chat history
- execution feeds
- approval cards
- timeline views
- project workspaces
- model selection
- memory browsing

---

# Backend

## Neo Daemon
Built with:
- Python 3.13
- FastAPI
- WebSockets

Responsibilities:
- orchestration
- memory
- planning
- review
- approvals
- task routing

---

# Runtime Layer

## OpenClaw
OpenClaw acts as:
- execution runtime
- tooling layer
- terminal bridge
- filesystem bridge

OpenClaw is:
- manually installed
- manually managed
- sandboxed locally
- isolated from personal system data

Neo NEVER installs OpenClaw automatically.

---

# AI Layer

## Neo Brain
Gemini 3.1 Pro High

## Fast Operations
Gemini Flash

---

# Memory Architecture

## SQLite
Stores:
- chats
- approvals
- execution logs
- history

## Vector Memory
Stores:
- architecture knowledge
- historical decisions
- summaries
- semantic retrieval

---

# Constitutional Engineering

Neo references:
- constitution.md
- architecture standards
- coding rules
- orchestration policies

before all major execution tasks.