# AgentMatt

AgentMatt is a full-stack AI agent platform inspired by Agno. It supports plugin
loading, multi-provider AI (Copilot and AWS Bedrock), permission gating, and
persistent chat history and memory.

## Highlights

- FastAPI backend with provider registry and plugin loader
- React frontend for chat, approvals, and provider settings
- Action logging with permission requests and audit trail
- Memory and learning endpoints for persistent context
- **MCP (Model Context Protocol) server support** with stdio and HTTP transports
- **Bitwarden integration** for secure credential management

## Architecture

- Backend: FastAPI, Python 3.x
- Frontend: React, react-scripts
- Storage: JSON files under backend/db/

## Quickstart

1. Backend setup
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install fastapi uvicorn boto3 pydantic httpx python-dotenv`
2. Frontend setup
   - `cd frontend && npm install`
3. Start both servers
   - `./start-servers.sh`

Ports:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Configuration

### AI Providers

Provider configuration lives in backend/config/providers.json. Use env var
placeholders to avoid committing secrets.

Required env vars for Bedrock:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (optional)
- `AWS_DEFAULT_REGION`

Copilot:
- `COPILOT_API_KEY`

##**MCP server configuration**: [MCP_SERVER_CONFIGURATION.md](MCP_SERVER_CONFIGURATION.md)
- **Bitwarden integration**: [BITWARDEN_INTEGRATION.md](BITWARDEN_INTEGRATION.md)
- Server management: [SERVER_MANAGEMENT.md](SERVER_MANAGEMENT.md)
- Bedrock integration notes: [AWS_BEDROCK_INTEGRATION.md](AWS_BEDROCK_INTEGRATION.md)
- Bedrock access setup: [SETUP_BEDROCK_ACCESS.md](SETUP_BEDROCK_ACCESS.md)
- Backend details: [backend/README.md](backend/README.md)
- Frontend details: [frontend/README.md](frontend/README.md)
- stdio transport for local processes
- Bitwarden references for secrets (e.g., `bw://ItemName/field`)

See [MCP_SERVER_CONFIGURATION.md](MCP_SERVER_CONFIGURATION.md) for detailed guide.

### Bitwarden Integration

Retrieve secrets from your Bitwarden vault via `bw serve`:

1. Start `bw serve --hostname localhost --port 8087`
2. Enable in backend/config/bitwarden.json
3. Use `bw://ItemName/field` syntax in configs

See [BITWARDEN_INTEGRATION.md](BITWARDEN_INTEGRATION.md) for setup guide.

## Useful Docs

- Server management: SERVER_MANAGEMENT.md
- Bedrock integration notes: AWS_BEDROCK_INTEGRATION.md
- Bedrock access setup: SETUP_BEDROCK_ACCESS.md
- Backend details: backend/README.md
- Frontend details: frontend/README.md

## Tests

- Backend: `pytest backend/tests`
- Frontend: `cd frontend && npm test`

## Troubleshooting

- Check logs: `./manage-servers.sh logs backend` or `./manage-servers.sh logs frontend`
- If ports are busy: `./stop-servers.sh`
