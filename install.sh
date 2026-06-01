#!/bin/bash
set -e

echo "Installing ChronoCode dependencies..."

# Detect OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

# Create virtual environment
if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    echo "Detected Apple Silicon. Forcing x86_64 for JPype/RefactoringMiner compatibility."
    arch -x86_64 python3 -m venv .venv_x86
    PYTHON_CMD="arch -x86_64 .venv_x86/bin/python"
    PIP_CMD="arch -x86_64 .venv_x86/bin/pip"
else
    python3 -m venv .venv
    PYTHON_CMD=".venv/bin/python"
    PIP_CMD=".venv/bin/pip"
fi

echo "Installing Python requirements..."
$PIP_CMD install -r requirements.txt

echo "Installing Frontend requirements..."
cd UI/web
npm install

echo "Installation complete!"
