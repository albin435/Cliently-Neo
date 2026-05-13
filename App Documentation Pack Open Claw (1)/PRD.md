# Neo — Product Requirements Document

## Vision

Neo is a native macOS AI CTO orchestration platform designed for personal use by Albin.

Neo is NOT a chatbot.

Neo is:
- a CTO
- orchestration layer
- supervisor
- reviewer
- governance system

The user only communicates with Neo through a dedicated internal communication interface inspired by:
- Codex
- Cursor
- Linear
- modern messenger UX

Instead of external messengers like Telegram or WhatsApp, Neo includes its own built-in communication workspace designed specifically for AI engineering orchestration.

---

# Core Architecture

User
↓
Neo Supervisor Layer
↓
OpenClaw Runtime
↓
Antigravity Execution Agents
↓
Filesystem / Tools / Terminal

---

# Responsibilities

## Neo
Handles:
- planning
- orchestration
- approvals
- reviews
- memory
- governance
- architecture integrity
- executive summaries

## OpenClaw
Handles:
- runtime tooling
- shell execution
- filesystem access
- automation
- skills execution

## Antigravity
Handles:
- implementation
- coding
- execution tasks
- engineering workflows

---

# OpenClaw Policy

Neo must NOT:
- install OpenClaw
- configure OpenClaw automatically
- initialize Docker automatically
- modify runtime infrastructure automatically

OpenClaw is manually managed by the user.

Neo may:
- connect to OpenClaw
- validate runtime health
- communicate with runtime APIs
- dispatch execution tasks

---

# Core Features

## Internal Communication Workspace
A built-in communication system inspired by:
- Codex
- Discord-style workspaces
- Cursor chat UX

Features:
- persistent chats
- execution threads
- project channels
- execution timeline
- multi-session history
- searchable memory

---

## Approval Workflow
Before execution Neo shows:
- risks
- execution plan
- affected files
- required tools
- runtime actions

---

## Workspace Intelligence
Neo understands:
- repository structure
- git state
- configs
- architecture
- project history
- technical decisions

---

## Execution Timeline
Every task includes:
- planning
- approvals
- execution
- retries
- review
- summary
- replayable history

---

# UX Direction

Inspired by:
- Codex
- Cursor
- Linear
- Arc
- Raycast

Design principles:
- calm
- premium
- operational
- technical
- keyboard-first
- information dense

---

# Key Principle

Neo supervises.
OpenClaw executes.
Antigravity implements.