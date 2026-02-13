# Data Model: AI Agent for Agno Compatibility

## Entities

- User
  - id
  - name
  - authorization_level

- ChatSession
  - id
  - user_id
  - start_time
  - end_time
  - provider (copilot/bedrock)

- ChatMessage
  - id
  - session_id
  - timestamp
  - sender (user/agent)
  - content
  - action_taken (optional)

- ActionLog
  - id
  - session_id
  - timestamp
  - action_type
  - status
  - permission_requested
  - permission_granted

- ProviderConfig
  - id
  - user_id
  - provider_name
  - config_data

- Memory
  - id
  - user_id
  - session_id
  - data
  - learned_at

## Relationships

- User has many ChatSessions
- ChatSession has many ChatMessages
- ChatSession has many ActionLogs
- User has many ProviderConfigs
- User has many Memories

