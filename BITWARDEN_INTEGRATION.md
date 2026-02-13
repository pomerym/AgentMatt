# Bitwarden Integration

AgentMatt can retrieve secrets from your Bitwarden vault via the `bw serve` HTTP API.

## Setup

1. **Start bw serve** (if not already running):
   ```sh
   bw login
   bw unlock
   export BW_SESSION="your-session-token"
   bw serve --hostname localhost --port 8087
   ```

2. **Configure AgentMatt**:
   Edit `backend/config/bitwarden.json`:
   ```json
   {
     "enabled": true,
     "base_url": "http://localhost:8087",
     "cache_ttl": 30,
     "timeout": 10,
     "aliases": {
       "jira_token": {
         "item": "Jira",
         "field": "api_token"
       },
       "mcp_auth": {
         "item": "MCP Server",
         "field": "token"
       }
     }
   }
   ```

3. **Use Bitwarden references in config**:
   
   **Direct reference**:
   ```json
   "api_key": "bw://Jira/api_token"
   ```
   
   **Alias reference**:
   ```json
   "token": "bw://jira_token"
   ```
   
   **Supported fields**:
   - `username`, `password`, `uri`, `notes`
   - Custom fields by name

## Example: MCP Server with Bitwarden Auth

In `backend/config/server.json`:
```json
{
  "mcp": {
    "servers": [
      {
        "id": "secure_mcp",
        "transport": "http",
        "url": "https://my-mcp-server.com",
        "headers": {
          "Authorization": "bw://mcp_auth"
        }
      }
    ]
  }
}
```

## Example: Provider Creds from Bitwarden

In `backend/config/providers.json`:
```json
{
  "providers": {
    "copilot": {
      "api_key": "bw://GitHub/copilot_token"
    }
  }
}
```

## Troubleshooting

- **Connection refused**: Ensure `bw serve` is running on port 8087.
- **Item not found**: Verify item name matches exactly (case-sensitive).
- **Field not found**: Check field name in Bitwarden (e.g., custom field names).
- **Cache stale**: Restart the backend or wait `cache_ttl` seconds.
