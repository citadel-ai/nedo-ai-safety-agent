#!/bin/bash

# Start script for Japan Procedures Agent
# This script starts both the backend and frontend services

set -e

echo "🚀 Starting Japan Procedures Agent..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found."
    echo "Please run: uv venv && source .venv/bin/activate && uv pip install -e '.[dev]'"
    echo "Or if you don't have uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Please create one based on env_template.txt"
fi

# Check if node_modules exists in frontend
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Create a PID directory if it doesn't exist
mkdir -p .pids

echo -e "${BLUE}Starting backend server...${NC}"
# Activate virtual environment and start backend in background
source .venv/bin/activate
python run_server.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .pids/backend.pid
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo "  Backend logs: logs/backend.log"
echo "  Backend API: http://localhost:8000"

# Wait a moment for backend to start
sleep 2

echo -e "${BLUE}Starting frontend dev server...${NC}"
# Start frontend in background
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../.pids/frontend.pid
cd ..
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "  Frontend logs: logs/frontend.log"
echo "  Frontend URL: http://localhost:3000"

echo ""
echo -e "${GREEN}✅ Application started successfully!${NC}"
echo ""
echo "📊 Services:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "To stop the application, run: ./stop.sh"
echo "To view frontend logs: tail -f logs/frontend.log"
echo ""
echo "════════════════════════════════════════════════════════"
echo "📋 Backend logs (Ctrl+C to stop viewing, services will continue running):"
echo "════════════════════════════════════════════════════════"
echo ""

# Tail the backend logs
tail -f logs/backend.log

