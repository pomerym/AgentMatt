# API Contracts: AI Agent for Agno Compatibility

## Endpoints

### Chat Session
- POST /api/chat/start
- GET /api/chat/{session_id}/history
- POST /api/chat/{session_id}/message

### AI Provider
- GET /api/provider/list
- POST /api/provider/select
- GET /api/provider/config
- POST /api/provider/config

### Permission & Authorization
- POST /api/action/request-permission
- GET /api/action/audit-log

### Learning & Memory
- GET /api/memory/{user_id}
- POST /api/memory/learn

## Mapping to User Stories

- Chat Session endpoints → US1
- AI Provider endpoints → US2
- Permission endpoints → US3
- Memory endpoints → US4

