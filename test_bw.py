#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend/src')

from bitwarden_client import BitwardenClient
from secret_resolver import resolve_secret_value

# Test Bitwarden connection
bw = BitwardenClient('http://localhost:8087')
print('Testing Bitwarden connection...')
items = bw.list_items()
print(f'Found {len(items)} items in Bitwarden')

# Look for Splunk DEV item
splunk_items = [i for i in items if 'splunk' in i.get('name', '').lower()]
print(f'Splunk items: {[i["name"] for i in splunk_items]}')

# Test resolution
test_ref = 'bw://Splunk DEV/password'
print(f'\nTesting resolution of: {test_ref}')
try:
    result = resolve_secret_value(test_ref)
    print(f'Resolved to: {result[:50]}...' if len(result) > 50 else f'Resolved to: {result}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
