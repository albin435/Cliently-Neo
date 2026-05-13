# Neo — Technical Requirements

# Frontend
- SwiftUI
- Tuist

# Backend
- Python 3.13
- FastAPI
- WebSockets

# Runtime
- OpenClaw
- local Docker sandbox

# AI Models
- Gemini 3.1 Pro High
- Gemini Flash

# Database
- SQLite
- ChromaDB

---

# Runtime Rules

OpenClaw:
- is NOT installed automatically
- is managed manually by Albin
- is treated as external runtime infrastructure

Neo:
- connects to OpenClaw
- validates runtime health
- dispatches execution tasks

---

# Required Features

## Communication System
- internal messenger/workspace
- persistent history
- project threads
- searchable conversations

## Supervisor System
- task contracts
- approvals
- orchestration
- review passes
- retry logic

## Runtime Integration
- filesystem access
- shell execution
- tool orchestration
- execution monitoring

---

# Security

- approval-gated execution
- restricted filesystem access
- local-first architecture
- Docker sandboxing
- workspace isolation