#!/bin/bash
# Quick check server status
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./manage-servers.sh status "$@"
