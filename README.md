# Neo (Cliently AI Daemon)

Neo is the proprietary AI "CTO" and autonomous daemon powering the Cliently ecosystem. Designed as a persistent, sovereign background agent, Neo bridges local execution with cloud intelligence, providing the user with an ever-present, context-aware digital co-founder.

This repository contains the core intelligence daemon and the macOS native menu-bar application that interfaces with it.

## 🧠 What is Neo?

Unlike traditional chatbots that sit passively in a browser tab, Neo is an active **Daemon**. It runs natively on your machine, constantly monitoring workflows, managing tasks, and executing multi-step autonomous plans. 

Neo is designed around the **"Sovereign CTO"** paradigm:
- **Local Context:** Neo hooks deeply into your local workspace, reading system telemetry, managing files, and operating your developer environment securely.
- **Agentic Workflows:** Through the `OpenClaw` engine and integrated MCP (Model Context Protocol) servers, Neo doesn't just answer questions—it *does* things. It can generate UI components, interface with your GitHub, manipulate databases, and automate your workflow.
- **Persistent Memory:** Utilizing vector storage and long-term memory structures, Neo remembers project constraints, architectural decisions, and user preferences across sessions.
- **Native Integration:** The Swift-based macOS application lives in your menu bar, ensuring Neo is always one click away without eating up your system resources.

## 🏗️ Architecture

The repository is split into two primary components:

### 1. The Daemon (`/daemon`)
A high-performance Python application built with FastAPI. It handles the heavy lifting of AI orchestration.
- **Engines:** Modular subsystems for specific tasks (e.g., `openclaw` for agentic coding, `mcp_manager` for tool connections, `memory` for persistence).
- **Extensibility:** Built to integrate with local tools, external APIs, and MCP protocols.

### 2. The Mac App (`/app`)
A native macOS application built with Swift and SwiftUI.
- **Menu Bar Presence:** A clean, unobtrusive interface living in your menu bar.
- **WebSockets / REST:** Communicates with the local Python daemon in real-time, streaming AI responses, rendering Markdown, and managing the active agent state.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- macOS (for the Swift app)
- [uv](https://github.com/astral-sh/uv) (for Python dependency management)
- Xcode (for building the Mac app)

### Running the Daemon
1. Navigate to the `daemon/` directory.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Set up your environment variables:
   Create a local `.env` file containing your API keys (e.g., Anthropic, OpenAI). *Note: `.env` files are excluded from version control.*
4. Start the server:
   ```bash
   ./run-daemon.sh
   # or
   uv run python -m src.main
   ```

### Running the Mac App
1. Navigate to the `app/` directory.
2. Use Tuist to generate the Xcode project:
   ```bash
   tuist generate
   ```
3. Open `Neo.xcworkspace` in Xcode.
4. Build and run the target.

## 🔒 Security & Privacy

As an agent capable of executing code and reading local files, security is paramount:
- **No Uploads:** Your code and files stay local unless explicitly transmitted to an LLM provider for processing.
- **Sandboxed Execution:** The OpenClaw engine ensures terminal commands and script executions are transparent and require confirmation for sensitive actions.
- **No Embedded Secrets:** All API keys and secrets must be provided via the local `.env` file. This repository contains zero hardcoded credentials.

## 📄 License

(C) Cliently. All rights reserved. 
This codebase is open-sourced for demonstration and integration purposes.
