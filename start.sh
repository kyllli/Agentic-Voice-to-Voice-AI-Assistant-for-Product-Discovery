#!/usr/bin/env bash
set -e

echo "Starting Unified FastAPI Server (UI + MCP)..."
uvicorn server:root_app --host 0.0.0.0 --port ${PORT:-8000}
