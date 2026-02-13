# Agno AI Agent Backend

## Quickstart

1. Install dependencies:
   - Python: fastapi, uvicorn
   - Run: `pip install fastapi uvicorn`
2. Start backend:
   - `uvicorn backend.src.main:app --reload`

## Endpoints
- /api/chat/start
- /api/chat/{session_id}/history
- /api/chat/{session_id}/message
- /api/provider/list
- /api/provider/select
- /api/provider/config
- /api/action/request-permission
- /api/action/audit-log
- /api/memory/{user_id}
- /api/memory/learn

## Configuration
- backend/config/server.json
- backend/config/providers.json

## Database
- backend/db/

## Skills
- backend/skills/agno/

