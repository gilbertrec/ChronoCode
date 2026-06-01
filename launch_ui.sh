#!/bin/bash

# Stop everything if one command fails
set -e

# Start backend in background
arch -x86_64 .venv_x86/bin/python UI/backend/server.py &
BACKEND_PID=$!

# Start frontend
cd UI/web
npm install
npm run dev

# When frontend stops, also stop backend
kill $BACKEND_PID