#!/bin/bash
# Update Splunk DEV item with encrypted MCP token in notes field

echo "Updating Splunk DEV Bitwarden item..."
echo ""
echo "Paste the encrypted token (874 characters) and press Enter:"
read -r TOKEN

if [ -z "$TOKEN" ]; then
    echo "Error: No token provided"
    exit 1
fi

TOKEN_LEN=${#TOKEN}
echo ""
echo "Token length: $TOKEN_LEN characters"

if [ $TOKEN_LEN -lt 800 ]; then
    echo "Warning: Token seems short. Expected ~874 characters."
    echo "Continue anyway? (y/n)"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "Aborted"
        exit 1
    fi
fi

# Get item ID
ITEM_ID=$(curl -s "http://localhost:8087/list/object/items?search=Splunk" | \
    python3 -c "import sys, json; data = json.load(sys.stdin); items = data.get('data', {}).get('data', []); print([i['id'] for i in items if 'Splunk DEV' in i.get('name', '')][0])")

if [ -z "$ITEM_ID" ]; then
    echo "Error: Could not find 'Splunk DEV' item"
    exit 1
fi

echo "Found item ID: $ITEM_ID"
echo ""

# Get current item
ITEM=$(curl -s "http://localhost:8087/object/item/$ITEM_ID")

# Update with notes (using bw CLI)
echo "To update via Bitwarden CLI, run:"
echo ""
echo "  bw get item '$ITEM_ID' | jq '.notes = \"$TOKEN\"' | bw encode | bw edit item '$ITEM_ID'"
echo ""
echo "Or manually edit in Bitwarden Desktop/Web:"
echo "  1. Open Bitwarden"
echo "  2. Find 'Splunk DEV'"
echo "  3. Click Edit"
echo "  4. Scroll to Notes section"
echo "  5. Paste the token"
echo "  6. Click Save"
echo "  7. Run: bw sync"
echo "  8. Restart bw serve"
