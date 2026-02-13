#!/usr/bin/env python3
import sys
import json
import os

# Change to the repo root
os.chdir('/Users/exp1x459/git/AgentMatt')
sys.path.insert(0, '/Users/exp1x459/git/AgentMatt')

# Import from backend package
from backend.src.secret_resolver import resolve_config, configure_bitwarden
from backend.src.bitwarden_client import BitwardenClient

# Initialize Bitwarden
bw_client = BitwardenClient('http://localhost:8087')

# Read bitwarden config
with open('backend/config/bitwarden.json') as f:
    bw_config = json.load(f)

print(f"Bitwarden enabled: {bw_config.get('enabled')}")
print(f"Configuring bitwarden with client: {bw_client is not None}")

configure_bitwarden(bw_client if bw_config.get('enabled') else None, bw_config.get('aliases', {}))

# Test a direct resolution
from backend.src.secret_resolver import resolve_secret_value
test_value = "bw://Splunk DEV/password"
print(f"\nDirect test resolution of: {test_value}")
try:
    resolved_test = resolve_secret_value(test_value)
    if len(resolved_test) > 50:
        print(f"Resolved to: {resolved_test[:30]}...{resolved_test[-20:]}")
    else:
        print(f"Resolved to: {resolved_test}")
except Exception as e:
    print(f"Error: {e}")

print()

# Read server config
with open('backend/config/server.json') as f:
    server_config = json.load(f)

# Get the MCP server config
mcp_servers = server_config.get('mcp', {}).get('servers', [])
if mcp_servers:
    server = mcp_servers[0]
    print(f"Server ID: {server.get('id')}")
    print(f"Transport: {server.get('transport')}")
    print(f"Command: {server.get('command')}")
    print(f"\nArgs:")
    
    # Resolve the config
    resolved = resolve_config(server)
    
    for i, arg in enumerate(resolved.get('args', [])):
        if 'Authorization' in arg and 'Bearer' in arg:
            # Truncate the token for display
            parts = arg.split('Bearer ')
            if len(parts) > 1:
                token = parts[1]
                if len(token) > 50:
                    print(f"  [{i}]: Authorization: Bearer {token[:30]}...{token[-20:]}")
                else:
                    print(f"  [{i}]: Authorization: Bearer {token}")
            else:
                print(f"  [{i}]: {arg}")
        else:
            print(f"  [{i}]: {arg}")
else:
    print("No MCP servers configured")
