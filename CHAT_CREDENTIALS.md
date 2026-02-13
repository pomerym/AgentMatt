# Using Bitwarden Credentials in Chat Sessions

AgentMatt now supports retrieving credentials directly within chat messages using the Bitwarden `bw://item/field` format. Credentials are automatically resolved on the backend before the message is sent to the AI provider.

## Format

```
bw://ItemName/field_name
```

## Examples

### Retrieve a Single Credential

In a chat message:
```
I need to authenticate. Can you use this token: bw://GitHub/api_token
```

### Retrieve Multiple Credentials

```
Connect to the database with these credentials:
- Host: bw://DatabaseServer/uri
- Username: bw://DatabaseServer/username
- Password: bw://DatabaseServer/password
```

### Use Bitwarden Aliases

```
Use this credential: bw://jira_token
```

(Where `jira_token` is defined as an alias in `backend/config/bitwarden.json`)

## Supported Fields

All standard Bitwarden fields are supported:
- `username` - Login username
- `password` - Login password
- `uri` - Login URI/URL
- `notes` - Item notes
- Custom fields - Any custom field by name

## Features

- **Automatic Resolution**: Credentials are resolved automatically before being sent to the AI provider
- **Embedded Support**: Credentials can be embedded within regular text messages
- **Multiple Credentials**: Use multiple credential references in a single message
- **Error Handling**: If a credential cannot be found, the reference stays as the original text
- **Alias Support**: Use short aliases defined in the Bitwarden configuration

## Security Notes

⚠️ **Important Security Considerations**:

1. **Backend Resolution**: Credentials are resolved on the backend before being sent to the AI provider
2. **AI Visibility**: The AI will see the actual credential values in its context
3. **Session History**: Credentials appear in session history and can be viewed by anyone with access to the session database
4. **Transmission**: Credentials are transmitted to the AI provider as part of the message content
5. **Best Practices**:
   - Use sensitive credentials only in trusted sessions
   - Consider the sensitivity of the AI provider being used
   - Review session history regularly
   - Use short-lived or limited-scope credentials where possible
   - Consider session isolation based on credential sensitivity

## Configuration

Bitwarden is configured in `backend/config/bitwarden.json`. Ensure:

1. `enabled` is set to `true`
2. `base_url` points to your `bw serve` instance
3. Aliases are properly configured for commonly-used credentials

See [BITWARDEN_INTEGRATION.md](BITWARDEN_INTEGRATION.md) for full setup instructions.

## Examples

### Example 1: API Authentication

**Chat Message**:
```
Can you authenticate with this Splunk instance using: bw://Splunk/api_token
```

**Backend Processing**:
1. Detects `bw://Splunk/api_token`
2. Retrieves API token from Bitwarden
3. Sends message with token resolved to AI provider
4. AI provider sees actual token value in context

### Example 2: Multi-Service Credentials

**Chat Message**:
```
Set up a backup with these credentials:
- AWS Access Key: bw://AWS/access_key
- AWS Secret Key: bw://AWS/secret_key
- Backup Bucket: bw://AWS/backup_bucket
```

### Example 3: Using Aliases

**Chat Message**:
```
Deploy using git credentials: bw://github_token
```

**Configuration** (in `backend/config/bitwarden.json`):
```json
{
  "aliases": {
    "github_token": {
      "item": "GitHub Personal Access Token",
      "field": "token"
    }
  }
}
```

## Troubleshooting

**Credential not found**: 
- Verify the Bitwarden item name matches exactly (case-sensitive)
- Check that the field name exists in the item
- Ensure `bw serve` is running

**Bitwarden connection error**:
- Verify `base_url` in `bitwarden.json` is correct
- Ensure `bw serve` is running: `bw serve --hostname localhost --port 8087`
- Check that the unlocked session is active: `export BW_SESSION="your-token"`

**Alias not working**:
- Ensure the alias is configured in `bitwarden.json`
- Verify the alias points to a valid item name
- Check that the specified field exists in the Bitwarden item

## API Reference

When a message containing `bw://` references is posted to `/api/chat/{session_id}/message`:

1. The message is stored in session history as-is
2. Before sending to the AI provider, credential references are resolved
3. The AI provider receives the message with credentials resolved
4. MCP commands from the AI response continue to work normally

See [MCP_SERVER_CONFIGURATION.md](MCP_SERVER_CONFIGURATION.md) for integrating Bitwarden with MCP tools.
