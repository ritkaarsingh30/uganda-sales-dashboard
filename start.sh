#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Uganda Dashboard 2026..."

pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1

echo "Starting FastAPI backend on port 8000..."
cd "$SCRIPT_DIR/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/uvicorn main:app --port 8000 --log-level warning &
BACKEND_PID=$!

echo "Waiting for backend..."
for i in {1..20}; do
  sleep 1
  if curl -s http://localhost:8000/api/health 2>/dev/null | grep -q "ok"; then
    echo "Backend ready."
    break
  fi
done

echo "Starting React frontend..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
sleep 2

echo ""
echo "Uganda Dashboard 2026"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
