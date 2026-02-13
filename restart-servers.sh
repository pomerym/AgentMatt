#!/bin/bash
# Quick restart servers
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./manage-servers.sh restart "$@"
