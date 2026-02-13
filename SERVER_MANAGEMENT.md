# Server Management Commands

AgentMatt includes convenient CLI commands for managing backend and frontend servers.

## Quick Start

From the project root directory:

```bash
# Start both servers
./start-servers.sh

# Stop both servers
./stop-servers.sh

# Restart both servers
./restart-servers.sh

# Check server status
./server-status.sh
```

## Advanced Usage

For more control, use the main management script:

```bash
./manage-servers.sh [command]
```

### Commands

- **start** - Start both backend and frontend servers (default)
- **stop** - Stop both backend and frontend servers
- **restart** - Restart both backend and frontend servers
- **status** - Check status of both servers
- **logs** - Tail server logs

### Examples

```bash
# Start servers
./manage-servers.sh start

# Check status
./manage-servers.sh status

# View backend logs
./manage-servers.sh logs backend

# View frontend logs
./manage-servers.sh logs frontend

# View all logs
./manage-servers.sh logs all

# Restart servers
./manage-servers.sh restart
```

## Server Details

- **Backend**: Port 8000 (FastAPI with uvicorn)
- **Frontend**: Port 3000 (React development server)
- **Log Directory**: `~/tmp/`

### Logs

After starting servers, you can view logs:

```bash
# Tail backend logs
tail -f ~/tmp/backend.log

# Tail frontend logs
tail -f ~/tmp/frontend.log

# Or use the management script
./manage-servers.sh logs backend
./manage-servers.sh logs frontend
```

## What Each Script Does

### start-servers.sh
- Kills any processes on ports 3000 and 8000
- Starts backend with uvicorn (with reload enabled)
- Starts frontend with npm start
- Creates ~/tmp directory for logs
- Shows server status and log locations

### stop-servers.sh
- Gracefully stops backend server
- Gracefully stops frontend server
- Verifies processes are killed

### restart-servers.sh
- Stops both servers
- Waits 1 second
- Starts both servers

### server-status.sh
- Shows if backend is running (port 8000)
- Shows if frontend is running (port 3000)
- Shows process IDs and log file locations

### manage-servers.sh
- Main management script
- Provides all above functionality
- Handles errors gracefully
- Color-coded output for clarity

## Manual Start (if scripts don't work)

```bash
# Terminal 1 - Backend
cd /Users/exp1x459/git/AgentMatt
source .venv/bin/activate
python -m uvicorn backend.src.main:app --reload --port 8000

# Terminal 2 - Frontend
cd /Users/exp1x459/git/AgentMatt/frontend
npm start
```

## Troubleshooting

### Ports Already in Use
The scripts automatically kill existing processes on ports 3000 and 8000. If issues persist:

```bash
# Kill processes on port 8000
lsof -ti:8000 | xargs kill -9

# Kill processes on port 3000
lsof -ti:3000 | xargs kill -9
```

### Missing Dependencies
The start script automatically:
- Activates the Python virtual environment
- Installs frontend dependencies if needed

If you still have issues, install manually:

```bash
# Backend dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
```

### Check Logs
Always start by checking the logs:

```bash
./manage-servers.sh logs backend
./manage-servers.sh logs frontend
```

## Integration with Development

You can add aliases to your shell profile for faster access:

```bash
# Add to ~/.zshrc or ~/.bash_profile
alias start-agentmatt='cd /Users/exp1x459/git/AgentMatt && ./start-servers.sh'
alias stop-agentmatt='cd /Users/exp1x459/git/AgentMatt && ./stop-servers.sh'
alias restart-agentmatt='cd /Users/exp1x459/git/AgentMatt && ./restart-servers.sh'
alias agentmatt-status='cd /Users/exp1x459/git/AgentMatt && ./server-status.sh'
```

Then from any terminal:

```bash
start-agentmatt
stop-agentmatt
restart-agentmatt
agentmatt-status
```
