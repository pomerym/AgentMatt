# Agno AI Agent Backend

## Quickstart

1. Install dependencies:
   - Create and activate a virtualenv: `python -m venv .venv && source .venv/bin/activate`
   - Install packages: `pip install fastapi uvicorn boto3 pydantic httpx python-dotenv`
2. Start backend:
   - `uvicorn backend.src.main:app --reload --port 8000`

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

### Environment Variables
Providers can resolve credentials from env vars when config values are placeholders.

- `COPILOT_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`

## Database
- backend/db/

## Skills
- backend/skills/agno/

