#!/bin/bash
set -e

cd "$(dirname "$0")/daemon"
uv sync
echo "Starting Neo Daemon v2..."
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8080
