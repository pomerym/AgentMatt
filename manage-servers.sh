#!/bin/bash

# AgentMatt Server Management CLI
# Usage: ./manage-servers.sh [start|stop|restart|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_PORT=8000
FRONTEND_PORT=3000
LOG_DIR="$PROJECT_ROOT/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check if a port is in use
is_port_in_use() {
    lsof -ti:"$1" > /dev/null 2>&1
}

# Function to stop a server on a specific port
stop_port() {
    local port=$1
    local name=$2
    
    if is_port_in_use "$port"; then
        print_status "Stopping $name on port $port..."
        lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
        sleep 1
        
        if is_port_in_use "$port"; then
            print_error "Failed to stop $name on port $port"
            return 1
        else
            print_success "Stopped $name"
            return 0
        fi
    else
        print_warning "$name is not running on port $port"
        return 0
    fi
}

# Function to start the backend
start_backend() {
    print_status "Starting backend server..."
    
    if is_port_in_use "$BACKEND_PORT"; then
        print_warning "Port $BACKEND_PORT is already in use. Stopping existing process..."
        stop_port "$BACKEND_PORT" "Backend"
    fi
    
    cd "$PROJECT_ROOT"

    if [ -f "$HOME/.zshrc" ]; then
        # Load user exports so local AWS env vars are available
        source "$HOME/.zshrc"
    fi

    if [ -f "$PROJECT_ROOT/.env" ]; then
        # Allow local project overrides without committing secrets
        source "$PROJECT_ROOT/.env"
    fi
    
    # Activate virtual environment and start backend
    source .venv/bin/activate
    nohup python -m uvicorn backend.src.main:app --reload --port "$BACKEND_PORT" > "$LOG_DIR/backend.log" 2>&1 &
    
    BACKEND_PID=$!
    sleep 2
    
    if is_port_in_use "$BACKEND_PORT"; then
        print_success "Backend started on port $BACKEND_PORT (PID: $BACKEND_PID)"
        print_status "Logs: tail -f $LOG_DIR/backend.log"
        return 0
    else
        print_error "Failed to start backend"
        tail -20 "$LOG_DIR/backend.log"
        return 1
    fi
}

# Function to start the frontend
start_frontend() {
    print_status "Starting frontend server..."
    
    if is_port_in_use "$FRONTEND_PORT"; then
        print_warning "Port $FRONTEND_PORT is already in use. Stopping existing process..."
        stop_port "$FRONTEND_PORT" "Frontend"
    fi
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install > /dev/null 2>&1
    fi
    
    nohup npm start > "$LOG_DIR/frontend.log" 2>&1 &

    FRONTEND_PID=$!

    local ready=false
    for i in {1..8}; do
        sleep 1
        if is_port_in_use "$FRONTEND_PORT"; then
            ready=true
            break
        fi
        if grep -q "Compiled successfully" "$LOG_DIR/frontend.log" 2>/dev/null; then
            ready=true
            break
        fi
    done

    if [ "$ready" = true ]; then
        print_success "Frontend started on port $FRONTEND_PORT (PID: $FRONTEND_PID)"
        print_status "Logs: tail -f $LOG_DIR/frontend.log"
        return 0
    else
        print_error "Failed to start frontend"
        tail -20 "$LOG_DIR/frontend.log"
        return 1
    fi
}

# Function to start all servers
start_all() {
    print_status "Starting AgentMatt servers..."
    echo ""
    
    start_backend || return 1
    echo ""
    start_frontend || return 1
    
    echo ""
    print_success "All servers started successfully!"
    return 0
}

# Function to stop all servers
stop_all() {
    print_status "Stopping AgentMatt servers..."
    echo ""
    
    stop_port "$BACKEND_PORT" "Backend"
    echo ""
    stop_port "$FRONTEND_PORT" "Frontend"
    
    echo ""
    print_success "All servers stopped"
    return 0
}

# Function to restart all servers
restart_all() {
    print_status "Restarting AgentMatt servers..."
    echo ""
    stop_all || true
    echo ""
    sleep 1
    start_all || return 1
}

# Function to check status
check_status() {
    print_status "Checking server status..."
    echo ""
    
    if is_port_in_use "$BACKEND_PORT"; then
        local backend_pid=$(lsof -ti:"$BACKEND_PORT")
        print_success "Backend is running (PID: $backend_pid, Port: $BACKEND_PORT)"
        echo "    Logs: tail -f $LOG_DIR/backend.log"
    else
        print_error "Backend is not running"
    fi
    
    echo ""
    
    if is_port_in_use "$FRONTEND_PORT"; then
        local frontend_pid=$(lsof -ti:"$FRONTEND_PORT")
        print_success "Frontend is running (PID: $frontend_pid, Port: $FRONTEND_PORT)"
        echo "    Logs: tail -f $LOG_DIR/frontend.log"
    else
        print_error "Frontend is not running"
    fi
    
    echo ""
    return 0
}

# Main command handler
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        check_status
        ;;
    logs)
        if [ -z "$2" ]; then
            print_error "Usage: $0 logs [backend|frontend|all]"
            exit 1
        fi
        
        case "$2" in
            backend)
                print_status "Tailing backend logs (Ctrl+C to exit)..."
                tail -f "$LOG_DIR/backend.log"
                ;;
            frontend)
                print_status "Tailing frontend logs (Ctrl+C to exit)..."
                tail -f "$LOG_DIR/frontend.log"
                ;;
            all)
                print_status "Tailing all logs (Ctrl+C to exit)..."
                tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
                ;;
            *)
                print_error "Unknown log target: $2"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "AgentMatt Server Management"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start       Start both backend and frontend servers (default)"
        echo "  stop        Stop both backend and frontend servers"
        echo "  restart     Restart both backend and frontend servers"
        echo "  status      Check status of both servers"
        echo "  logs        Tail server logs"
        echo ""
        echo "Log commands:"
        echo "  logs backend    Tail backend logs"
        echo "  logs frontend   Tail frontend logs"
        echo "  logs all        Tail all logs"
        echo ""
        echo "Environment:"
        echo "  Backend Port: $BACKEND_PORT"
        echo "  Frontend Port: $FRONTEND_PORT"
        echo "  Log Directory: $LOG_DIR"
        echo ""
        exit 1
        ;;
esac
