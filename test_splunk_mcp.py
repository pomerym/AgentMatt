#!/usr/bin/env python3
"""Test Splunk MCP connection with updated encrypted token"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.secret_resolver import resolve_config

# Load server config and resolve secrets
import json
with open('backend/config/server.json') as f:
    config = json.load(f)

# Resolve all secrets
resolved_config = resolve_config(config)

# Get Splunk server config
splunk_server = resolved_config['mcp']['servers'][0]

print("=" * 60)
print("SPLUNK MCP SERVER CONFIGURATION")
print("=" * 60)
print(f"ID: {splunk_server['id']}")
print(f"Name: {splunk_server['name']}")
print(f"Transport: {splunk_server['transport']}")
print(f"Command: {splunk_server['command']}")
print(f"URL (in args): {splunk_server['args'][2]}")
print()

# Check token resolution
auth_header = splunk_server['args'][4]
if auth_header.startswith("Authorization: Bearer "):
    token = auth_header.replace("Authorization: Bearer ", "")
    print(f"Token resolved: Yes")
    print(f"Token length: {len(token)} characters")
    print(f"Token preview: {token[:50]}...{token[-50:]}")
    print()
    
    if len(token) < 100:
        print("⚠️  WARNING: Token seems too short!")
        print("   Expected: ~1000+ characters (encrypted token)")
        print("   Got: {} characters".format(len(token)))
        print()
        print("   Please verify you generated an ENCRYPTED token from")
        print("   the Splunk MCP Server app, not a regular JWT token.")
    elif len(token) > 900:
        print("✓ Token length looks correct for encrypted token!")
        print()
        print("Environment variables:")
        for key, value in splunk_server.get('env', {}).items():
            print(f"  {key}: {value}")
        print()
        print("Testing connection with npx mcp-remote...")
        print("-" * 60)
    else:
        print("? Token length is in between (~{} chars)".format(len(token)))
        print("  This may or may not be correct. Attempting connection...")
        print()
else:
    print(f"⚠️  WARNING: Authorization header not in expected format")
    print(f"   Got: {auth_header}")

print()
print("To test connection, run:")
print()
print('  NODE_TLS_REJECT_UNAUTHORIZED=0 npx -y mcp-remote \\')
print(f'    "{splunk_server["args"][2]}" \\')
print(f'    --header "{auth_header}"')
print()
