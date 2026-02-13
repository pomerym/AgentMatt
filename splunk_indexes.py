#!/usr/bin/env python3
"""Query and display Splunk indexes"""

import json
import urllib.request

# Call the MCP API
req = urllib.request.Request(
    "http://localhost:8000/api/mcp/call",
    data=json.dumps({
        "server_id": "Splunk_DEV",
        "tool_name": "splunk_get_indexes",
        "arguments": {"row_limit": 100}
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))
results = data.get('result', {}).get('structuredContent', {}).get('results', [])

print(f'\n{"="*80}')
print(f'SPLUNK DEV - INDEX SUMMARY')
print(f'{"="*80}\n')
print(f'Total Indexes Found: {len(results)}')
print(f'Server: {results[0]["splunk_server"] if results else "N/A"}\n')

# Group by type
internal_indexes = [r for r in results if r['title'].startswith('_')]
app_indexes = [r for r in results if not r['title'].startswith('_')]

print(f'{"─"*80}')
print(f'INTERNAL/SYSTEM INDEXES ({len(internal_indexes)}):')
print(f'{"─"*80}')
for idx in sorted(internal_indexes, key=lambda x: x['title']):
    size = idx['currentDBSizeMB']
    events = idx['totalEventCount']
    status = "✓" if idx['disabled'] == "0" else "✗"
    print(f'  {status} {idx["title"]:25} │ Size: {size:>6} MB │ Events: {events:>12}')

print(f'\n{"─"*80}')
print(f'APPLICATION/DATA INDEXES ({len(app_indexes)}):')
print(f'{"─"*80}')

# Show interesting categories
categories = {}
for idx in app_indexes:
    prefix = idx['title'].split('_')[0] if '_' in idx['title'] else idx['title']
    if prefix not in categories:
        categories[prefix] = []
    categories[prefix].append(idx)

for category in sorted(categories.keys())[:15]:
    print(f'\n  {category}:')
    for idx in sorted(categories[category], key=lambda x: x['title'])[:5]:
        size = idx['currentDBSizeMB']
        events = idx['totalEventCount']
        status = "✓" if idx['disabled'] == "0" else "✗"
        print(f'    {status} {idx["title"]:30} │ Size: {size:>6} MB │ Events: {events:>12}')
    if len(categories[category]) > 5:
        print(f'    ... and {len(categories[category]) - 5} more {category} indexes')

print(f'\n{"="*80}\n')
