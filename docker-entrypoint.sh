#!/bin/bash
set -e

# Fix permissions for mounted volumes
# This runs as root to fix permissions, then switches to app user
if [ "$(id -u)" = "0" ]; then
    # Create and fix permissions for data directory
    mkdir -p /app/data/chroma_db
    chown -R app:app /app/data || true
    chmod -R 755 /app/data || true
    
    # Create and fix permissions for logs directory
    mkdir -p /var/log/ai-demo
    chown -R app:app /var/log/ai-demo || true
    chmod -R 755 /var/log/ai-demo || true
    
    # Switch to app user and execute the command
    exec gosu app "$@"
else
    # Already running as app user, just execute
    exec "$@"
fi
