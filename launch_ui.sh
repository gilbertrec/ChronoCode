#!/bin/bash
set -e

# Detect OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

# Path to python
if [ -d ".venv_x86" ] && [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    PYTHON_CMD="arch -x86_64 .venv_x86/bin/python"
elif [ -d ".venv_x86" ]; then
    PYTHON_CMD=".venv_x86/bin/python"
elif [ -d ".venv" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# Start backend in background
$PYTHON_CMD UI/backend/server.py &
BACKEND_PID=$!

# Start frontend
cd UI/web
npm install
npm run dev

# When frontend stops, also stop backend
kill $BACKEND_PID