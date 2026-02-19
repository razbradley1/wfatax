#!/usr/bin/env bash
# Start the Tax Planner application in development mode.
# Usage: ./start.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Tax Planner – Development Start ==="

# ---- Backend ----
echo "[1/2] Starting backend …"
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Start uvicorn in the background
cd "$SCRIPT_DIR"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "      Backend running (PID $BACKEND_PID) → http://localhost:8000"

# ---- Frontend ----
echo "[2/2] Starting frontend …"
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install
fi

npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
echo "      Frontend running (PID $FRONTEND_PID) → http://localhost:5173"

echo ""
echo "=== Both services running. Press Ctrl+C to stop. ==="

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
