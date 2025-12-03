#!/bin/bash

# Song Structure Replicator - Unified Startup Script
# Runs both backend (FastAPI) and frontend (Vite) servers in parallel
#
# Before running, make sure this script is executable:
#   chmod +x run.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    print_info "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    print_success "Servers stopped."
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT SIGTERM

# Check if uvicorn is installed
print_info "Checking for uvicorn..."
if ! command -v uvicorn &> /dev/null; then
    print_error "uvicorn is not installed!"
    print_info "Please install it with:"
    echo "  pip install uvicorn"
    echo ""
    print_info "Or install all backend dependencies:"
    echo "  pip install -r backend/requirements.txt"
    exit 1
fi
print_success "uvicorn found"

# Check if npm is installed
print_info "Checking for npm..."
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed!"
    print_info "Please install Node.js and npm first."
    exit 1
fi
print_success "npm found"

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    print_warning "Frontend dependencies not found. Installing..."
    npm --prefix frontend install
    print_success "Frontend dependencies installed"
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_info "Starting servers..."
echo ""

# Start backend server
print_info "Starting backend server on http://localhost:8000"
# Set PYTHONPATH to include backend/src so imports work correctly
export PYTHONPATH="${SCRIPT_DIR}/backend/src:${PYTHONPATH}"
uvicorn backend.src.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Start frontend server
print_info "Starting frontend server on http://localhost:5173"
npm --prefix frontend run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a moment for servers to start
sleep 2

# Check if processes are still running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    print_error "Backend server failed to start. Check /tmp/backend.log for details."
    cat /tmp/backend.log
    exit 1
fi

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    print_error "Frontend server failed to start. Check /tmp/frontend.log for details."
    cat /tmp/frontend.log
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Backend server running (PID: $BACKEND_PID)"
print_success "Frontend server running (PID: $FRONTEND_PID)"
echo ""
print_info "Backend API: http://localhost:8000"
print_info "Frontend App: http://localhost:5173"
print_info "API Docs: http://localhost:8000/docs"
echo ""
print_info "Press Ctrl+C to stop both servers"
echo ""

# Tail logs from both servers
tail -f /tmp/backend.log /tmp/frontend.log &
TAIL_PID=$!

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
kill $TAIL_PID 2>/dev/null || true

