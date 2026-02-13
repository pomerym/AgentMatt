# MCP Server Configuration Guide

AgentMatt provides a UI for configuring MCP (Model Context Protocol) servers with support for Bitwarden secret references.

## Accessing MCP Configuration

1. **Open Settings**: Click the "Settings" button in the left sidebar
2. **Navigate to MCP Servers**: Click the "MCP Servers" tab
3. **Add a Server**: Click "+ Add Server"

## Configuration Options

### HTTP Transport

For HTTP-based MCP servers:

- **Server ID**: Unique identifier (e.g., `splunk_dev`)
- **Name**: Display name (e.g., `Splunk DEV`)
- **Transport**: Select `HTTP`
- **URL**: Full endpoint URL (e.g., `https://beneva-dev.splunkcloud.com:8089/services/mcp`)
- **Headers**: JSON object with authentication headers

### stdio Transport

For local MCP servers running via stdin/stdout:

- **Server ID**: Unique identifier (e.g., `local_mcp`)
- **Name**: Display name
- **Transport**: Select `stdio`
- **Command**: Executable command (e.g., `python`, `node`)
- **Args**: Space-separated arguments (e.g., `-m my_mcp_server`)
- **CWD**: Working directory (optional)
- **Env**: JSON object with environment variables (optional)

## Using Bitwarden for Credentials

### Prerequisites

1. **Start Bitwarden serve**:
   ```sh
   bw login
   bw unlock
   export BW_SESSION="your-session-token"
   bw serve --hostname localhost --port 8087
   ```

2. **Enable Bitwarden in AgentMatt**:
   Edit `backend/config/bitwarden.json`:
   ```json
   {
     "enabled": true,
     "base_url": "http://localhost:8087",
     "cache_ttl": 30
   }
   ```

### Example: Splunk DEV with Bitwarden Auth

1. **Create Bitwarden Item**:
   - Item Name: `Splunk DEV MPC`
   - Add custom field or use password field for the auth token

2. **Configure MCP Server**:
   - Server ID: `splunk_dev`
   - Name: `Splunk DEV`
   - Transport: `HTTP`
   - URL: `https://beneva-dev.splunkcloud.com:8089/services/mcp`
   - Headers:
     ```json
     {
       "Authorization": "bw://Splunk DEV MPC/password"
     }
     ```

3. **Save**: Click "Save" button

### Bitwarden Reference Syntax

**Direct reference**:
```
bw://<ItemName>/<field>
```

**Supported fields**:
- `username` - Login username
- `password` - Login password
- `uri` - First URI in the item
- `notes` - Secure notes
- `<custom_field_name>` - Any custom field name

**Examples**:
```json
{
  "Authorization": "bw://Splunk DEV MPC/password",
  "X-API-Key": "bw://My API Keys/api_token",
  "X-Custom": "bw://Credentials/custom_field_name"
}
```

## Using MCP Tools

### Via Chat Commands

Once a server is configured, use `/mcp` commands:

```
/mcp servers                    # List configured servers
/mcp list                       # List all available tools
/mcp <server_id> <tool_name>    # Call a tool
/mcp <server_id> <tool_name> {"arg": "value"}  # Call with arguments
```

**Example**:
```
/mcp splunk_dev search_logs {"query": "error", "from": "-1h"}
```

### Via Sidebar

MCP tools appear in the left sidebar under the "Tools" section. They show as:
```
<server_id>/<tool_name> - description
```

## Troubleshooting

### SSL Certificate Errors

If you see SSL certificate errors (common with self-signed certificates), you may need to:
- Use a verified certificate
- Configure your environment to trust the certificate
- Or contact your MCP server administrator

### Connection Refused

- Verify the MCP server URL is correct
- Check that the server is running and accessible
- Verify firewall rules allow the connection

### Authentication Failures

- Verify Bitwarden references are correct
- Check that `bw serve` is running
- Confirm the Bitwarden item name and field match exactly (case-sensitive)
- Test the credential directly in Bitwarden CLI: `bw get item "Splunk DEV MPC"`

### Tool List Empty

- Wait a few seconds after adding a server (tools are cached)
- Check backend logs for connection errors: `tail -f logs/backend.log`
- Try refreshing the page

## Example Configurations

### GitHub API via MCP

```json
{
  "id": "github_api",
  "name": "GitHub API",
  "transport": "http",
  "url": "https://api.github.com/mcp",
  "headers": {
    "Authorization": "token bw://GitHub/api_token",
    "Accept": "application/vnd.github.v3+json"
  }
}
```

### Local Python MCP Server

```json
{
  "id": "local_tools",
  "name": "Local Tools",
  "transport": "stdio",
  "command": "python",
  "args": ["-m", "my_mcp_server"],
  "cwd": "/Users/me/mcp-servers",
  "env": {
    "MCP_API_KEY": "bw://Local MCP/api_key"
  }
}
```

## Editing and Deleting Servers

- **Edit**: Click the "Edit" button next to a server in the list
- **Delete**: Click the "Delete" button and confirm
- Changes take effect immediately and refresh the tools list

## Storage

MCP server configurations are stored in:
```
backend/config/server.json
```

Under the `mcp.servers` array. You can also edit this file directly and restart the backend.
