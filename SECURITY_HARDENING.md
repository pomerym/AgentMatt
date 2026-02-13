# Security Hardening Implementation

This document outlines the security improvements made to AgentMatt and how to configure them.

## Overview

AgentMatt has been hardened against unauthorized access and malicious command execution:

### 1. API Key Authentication
- All endpoints except `/api/health` require an API key
- Supports `Authorization: Bearer <key>` or `X-API-Key: <key>` headers
- Rate limiting: 60 requests per minute per API key

**Configuration:**
```bash
export AGENTMATT_API_KEY="your-secure-api-key-here"
```

### 2. CORS Configuration
- Previously allowed all origins (`*`)
- Now restricted to configured origins (default: localhost)
- Configure with environment variable:

```bash
export AGENTMATT_CORS_ORIGINS="localhost,127.0.0.1,https://yourdomain.com"
```

### 3. Command Execution Allowlist
- Only approved command patterns can be executed
- Prevents execution of dangerous commands (rm -rf /, sudo, etc.)
- Commands are validated before execution
- Output is sanitized to remove sensitive data

**Allowed command categories:**
- Splunk CLI operations
- Safe utilities (ls, cat, grep, find, etc.)
- Python scripts from the project
- Git safe operations (status, log, diff)
- HTTPS/HTTPS curl requests

**Denied patterns:**
- Recursive root deletion `rm -rf /`
- Writes to /etc directory
- `sudo` commands
- Overly permissive `chmod 777`
- Command chaining with rm
- Backticks and $() command substitution
- Piping to netcat

### 4. Audit Logging
- All authentication attempts logged to `/tmp/agentmatt-audit.log`
- All command extractions logged
- All command approvals/denials logged
- Format: JSON for easy parsing

**Log entries include:**
- Timestamp
- Action type (AUTH_CHECK, COMMAND_EXTRACTED, COMMAND_APPROVED, etc.)
- Resource accessed
- API key (last 4 chars only)
- Status code
- Error messages (if any)

### 5. Error Message Sanitization
- Error messages don't leak internal paths
- Exception details are generic
- Sensitive data patterns are redacted

### 6. Rate Limiting
- Simple in-memory rate limiting
- 60 requests per minute per API key
- Returns 429 (Too Many Requests) when exceeded

## Multi-User Deployment Checklist

For production deployment with multiple users:

- [ ] Generate unique API keys for each user/service
- [ ] Use a proper secrets manager (AWS Secrets Manager, Vault, etc.)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS origins to specific domains
- [ ] Use database-backed rate limiting instead of in-memory
- [ ] Enable persistent audit logging to a database
- [ ] Set up monitoring and alerting for failed auth attempts
- [ ] Implement API key rotation policy
- [ ] Add user-specific permission boundaries
- [ ] Implement request signing for critical operations
- [ ] Use environment-specific configurations
- [ ] Regular security audits and penetration testing

## Configuration Files

Create `.env` or similar for local development:
```
AGENTMATT_API_KEY=dev-insecure-change-in-production
AGENTMATT_CORS_ORIGINS=localhost,127.0.0.1
```

For production:
```
AGENTMATT_API_KEY=<strong-random-key-from-secrets-manager>
AGENTMATT_CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

## Monitoring Audit Logs

Monitor the audit log file:
```bash
# Watch for failed auth attempts
grep "403\|401\|429" /tmp/agentmatt-audit.log

# Watch for denied commands
grep "COMMAND_DENIED" /tmp/agentmatt-audit.log

# Monitor failed API calls
tail -f /tmp/agentmatt-audit.log | grep "error"
```

## Testing the Security Features

### 1. Test API Key Requirement
```bash
# Without API key (should fail)
curl http://localhost:8000/api/chat/sessions

# With API key
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/chat/sessions
```

### 2. Test Command Allowlist
```bash
# Allowed command
curl -X POST http://localhost:8000/api/chat/{session}/message \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "/cmd ls /tmp"}'

# Denied command (should fail)
# This will be detected and blocked before execution
```

### 3. Test Rate Limiting
```bash
# Make 61 requests rapidly - should get 429 on 61st
for i in {1..61}; do
  curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health
done
```

## Future Improvements

- [ ] Multi-tenant support with user IDs
- [ ] JWT tokens instead of static keys
- [ ] Command execution sandboxing (containers)
- [ ] Bitwarden-backed secret rotation
- [ ] Fine-grained permission scopes
- [ ] Database-backed audit logs
- [ ] IP address whitelisting
- [ ] Request signing for critical operations
