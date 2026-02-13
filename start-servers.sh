#!/bin/bash
# Quick start servers
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./manage-servers.sh start "$@"
