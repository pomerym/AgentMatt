#!/bin/bash
# Quick stop servers
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./manage-servers.sh stop "$@"
