#!/bin/bash

# Stop script for Japan Procedures Agent
# This script stops both the backend and frontend services

echo "🛑 Stopping Japan Procedures Agent..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to kill process by PID file
kill_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${RED}Stopping $service_name (PID: $PID)...${NC}"
            kill $PID 2>/dev/null || true
            # Wait a moment for graceful shutdown
            sleep 1
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID 2>/dev/null || true
            fi
            echo -e "${GREEN}✓ $service_name stopped${NC}"
        else
            echo "⚠️  $service_name not running (stale PID file)"
        fi
        rm "$pid_file"
    else
        echo "⚠️  $service_name PID file not found"
    fi
}

# Kill services
kill_service "Backend" ".pids/backend.pid"
kill_service "Frontend" ".pids/frontend.pid"

# Also kill any remaining processes on the ports
echo ""
echo "Cleaning up any remaining processes..."

# Kill anything on port 8000 (backend)
BACKEND_PIDS=$(lsof -ti:8000 2>/dev/null || true)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "Killing processes on port 8000: $BACKEND_PIDS"
    kill -9 $BACKEND_PIDS 2>/dev/null || true
fi

# Kill anything on port 3000 (frontend)
FRONTEND_PIDS=$(lsof -ti:3000 2>/dev/null || true)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "Killing processes on port 3000: $FRONTEND_PIDS"
    kill -9 $FRONTEND_PIDS 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ Application stopped successfully!${NC}"

