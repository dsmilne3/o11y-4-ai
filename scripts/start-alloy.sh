#!/bin/bash
# Start Grafana Alloy with the demo configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_DIR/config/config.alloy"
ENV_FILE="$PROJECT_DIR/config/alloy.env"

echo "🔧 Starting Grafana Alloy for AI Observability Demo"

# Check if Alloy is available
if ! command -v alloy >/dev/null 2>&1; then
    echo "❌ Grafana Alloy is not installed"
    echo ""
    echo "Please install Grafana Alloy:"
    echo "  macOS: brew install grafana/grafana/alloy"
    echo "  Linux: See https://grafana.com/docs/alloy/latest/set-up/install/"
    echo "  Windows: Download from GitHub releases"
    echo ""
    echo "Or use Docker:"
    echo "  docker run -d --name alloy \\"
    echo "    -p 12345:12345 -p 4317:4317 -p 4318:4318 \\"
    echo "    -v $CONFIG_FILE:/etc/alloy/config.alloy:ro \\"
    echo "    --env-file $ENV_FILE \\"
    echo "    grafana/alloy:latest run /etc/alloy/config.alloy"
    exit 1
fi

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Alloy configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Load environment variables if env file exists
if [ -f "$ENV_FILE" ]; then
    echo "📋 Loading environment from: $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  Environment file not found: $ENV_FILE"
    echo "   Creating from example..."
    cp "$PROJECT_DIR/config/alloy.env.example" "$ENV_FILE"
    echo "   Please edit $ENV_FILE with your Grafana Cloud credentials"
fi

echo "🚀 Starting Alloy with configuration: $CONFIG_FILE"

# Start Alloy
alloy run \
    "$CONFIG_FILE" \
    --server.http.listen-addr=0.0.0.0:12345 \
    --disable-reporting \
    --stability.level=experimental

echo "✅ Alloy started successfully"
echo "   HTTP UI: http://localhost:12345"
echo "   OTLP gRPC: localhost:4317"
echo "   OTLP HTTP: localhost:4318"