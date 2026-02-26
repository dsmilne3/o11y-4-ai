#!/bin/bash
# Quick start script for AI Observability Demo

set -e

echo "🚀 Starting AI Observability Demo Setup"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists pip; then
    echo "❌ pip is required but not installed" 
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create and activate virtual environment
echo "🔧 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    # Temporarily disable exit on error to catch venv creation failure
    set +e
    venv_error=$(python3 -m venv venv 2>&1)
    venv_exit_code=$?
    set -e
    
    if [ $venv_exit_code -ne 0 ] || [ ! -d "venv" ]; then
        echo ""
        echo "❌ Failed to create virtual environment"
        if [ -n "$venv_error" ]; then
            echo ""
            echo "Error details:"
            echo "$venv_error" | sed 's/^/   /'
        fi
        echo ""
        echo "The python3-venv package is required but not installed."
        echo ""
        echo "On Debian/Ubuntu systems, install it with:"
        echo "  sudo apt-get update && sudo apt-get install -y python3-venv"
        echo ""
        echo "On macOS, it should be included with Python."
        echo "On other systems, install the python3-venv package for your distribution."
        exit 1
    fi
fi

# Verify venv exists before activation
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment directory not found"
    exit 1
fi

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    if [ ! -f "venv/Scripts/activate" ]; then
        echo "❌ Virtual environment activation script not found (venv/Scripts/activate)"
        exit 1
    fi
    source venv/Scripts/activate
else
    # macOS/Linux
    if [ ! -f "venv/bin/activate" ]; then
        echo "❌ Virtual environment activation script not found (venv/bin/activate)"
        echo "   The venv may not have been created correctly."
        exit 1
    fi
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Setup environment
echo "⚙️  Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
    echo "   Required: OPENAI_API_KEY"
    echo "   Optional: GRAFANA_CLOUD_* for remote telemetry"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/chroma_db
mkdir -p logs

echo "✅ Data directories created"

# Check if Docker is available
if command_exists docker; then
    echo "🐳 Docker detected - you can use 'docker-compose up' for containerized deployment"
else
    echo "ℹ️  Docker not found - running in local mode only"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start the application:"
echo "   python -m uvicorn app.main:app --reload"
echo "3. Run demo scenarios:"
echo "   python scripts/demo_scenarios.py"
echo "4. View metrics at http://localhost:8000/metrics"
echo "5. View API docs at http://localhost:8080/docs"
echo ""
echo "For Docker deployment:"
echo "   docker-compose up --build"
echo ""