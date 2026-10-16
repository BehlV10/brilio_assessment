#!/bin/bash
set -e

echo "=========================================================="
echo " Starting Listing Search Service (Backend + Frontend)"
echo "=========================================================="

# 1. Start Backend
echo "Starting FastAPI backend on http://127.0.0.1:8000..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment and installing backend requirements..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Start Frontend
echo "Starting Vite React frontend on http://localhost:5173..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend npm packages..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

echo ""
echo " Backend running at:  http://127.0.0.1:8000 (API Docs at /docs)"
echo " Frontend running at: http://localhost:5173"
echo " Press Ctrl+C to stop both servers."
echo "=========================================================="

wait
