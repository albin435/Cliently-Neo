# Neo — Architecture

# High-Level Architecture

User
↓
Neo Supervisor Layer
↓
Execution Providers
↓
Antigravity Agents

---

# Core Components

## Neo Core
Handles:
- orchestration
- planning
- governance
- memory
- validation

## Execution Providers
Abstract execution systems:
- Antigravity
- future providers
- local agents
- CLI agents

## Review Layer
Ensures:
- architectural integrity
- code quality
- execution correctness

## Memory Layer
Stores:
- conversations
- project knowledge
- technical decisions
- historical execution

---

# Pipeline

1. User Intent
2. Context Collection
3. Strategic Planning
4. Task Contract Generation
5. Approval Request
6. Delegation
7. Execution Monitoring
8. Review Pass
9. Executive Summary

---

# Constitutional Engineering

Neo references:
- architecture rules
- coding standards
- dependency restrictions
- naming conventions
- UI philosophy
- anti-pattern lists

File:
`constitution.md`

---

# Execution Contracts

Each task generates:

- objective
- constraints
- success criteria
- risks
- required approvals
- validation checks

---

# Data Flow

SwiftUI App
↔ WebSocket
↔ FastAPI Daemon
↔ Orchestrator
↔ Antigravity Bridge
↔ Antigravity Agents

---

# Persistence

## SQLite
- chats
- tasks
- approvals
- execution history

## Vector DB
- semantic memory
- architecture retrieval
- context recall