#!/bin/bash
# ===========================================
# NidanMitra AI - Native Run Script (Mac with MPS)
# ===========================================
# This script runs the backend natively with MPS acceleration
# while keeping PostgreSQL, Redis, and Qdrant in Docker

set -e

echo "🏥 NidanMitra AI - Starting with MPS acceleration"
echo "================================================"

# Find compatible Python version (3.11 or 3.12)
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python 3.11: $PYTHON_VERSION"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    PYTHON_VERSION=$(python3.12 --version 2>&1 | awk '{print $2}')
    echo "✅ Found Python 3.12: $PYTHON_VERSION"
else
    # Check default python3
    DEFAULT_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    DEFAULT_MAJOR=$(echo $DEFAULT_VERSION | cut -d. -f1)
    DEFAULT_MINOR=$(echo $DEFAULT_VERSION | cut -d. -f2)
    
    if [ "$DEFAULT_MAJOR" -eq 3 ] && [ "$DEFAULT_MINOR" -ge 11 ] && [ "$DEFAULT_MINOR" -lt 14 ]; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "✅ Using default Python: $PYTHON_VERSION"
    else
        echo "❌ Error: No compatible Python version found"
        echo "   Default Python: $(python3 --version 2>&1)"
        echo ""
        echo "📦 Solutions:"
        echo "   1. Install Python 3.11 or 3.12:"
        echo "      brew install python@3.11"
        echo "      or"
        echo "      brew install python@3.12"
        echo ""
        echo "   2. Use Docker instead (easiest, recommended):"
        echo "      docker compose up -d"
        echo ""
        exit 1
    fi
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found!"
    echo "   Creating from template..."
    echo ""
    echo "# NidanMitra AI Configuration" > .env
    echo "HF_TOKEN=" >> .env
    echo "USE_LOCAL_MODEL=true" >> .env
    echo "DEVICE=auto" >> .env
    echo "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/claricare" >> .env
    echo "REDIS_URL=redis://localhost:6379/0" >> .env
    echo "SECRET_KEY=change-this-in-production" >> .env
    echo ""
    echo "📝 Please edit .env and add your HF_TOKEN from HuggingFace"
    echo "   Get your token at: https://huggingface.co/settings/tokens"
    echo ""
fi

# Check if virtual environment exists or needs to be recreated
if [ ! -d "app/venv" ]; then
    echo "📦 Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv app/venv
elif [ -d "app/venv" ]; then
    # Check if existing venv uses wrong Python version
    VENV_PYTHON=$(app/venv/bin/python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    VENV_MINOR=$(echo $VENV_PYTHON | cut -d. -f2)
    if [ "$VENV_MINOR" -ge 14 ]; then
        echo "⚠️  Existing venv uses Python 3.14+ (incompatible)"
        echo "   Recreating with $PYTHON_CMD..."
        rm -rf app/venv
        $PYTHON_CMD -m venv app/venv
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source app/venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip setuptools wheel
echo "   Installing packages (this may take a few minutes)..."
pip install -q -r requirements.txt || {
    echo ""
    echo "❌ Error: Failed to install dependencies"
    echo "   If you're using Python 3.14+, try using Python 3.11 or 3.12 instead:"
    echo "   python3.11 -m venv app/venv"
    echo "   or"
    echo "   python3.12 -m venv app/venv"
    exit 1
}

# Fix packaging version conflict (langchain-core requires <24.0, wheel requires >=24.0)
# Install compatible version after requirements to override
echo "   Fixing packaging version conflicts..."
pip install -q "packaging>=23.2,<24.0" 2>/dev/null || true

# Start Docker services
echo "🐳 Starting Docker services (PostgreSQL, Redis, Qdrant)..."
if ! docker info >/dev/null 2>&1; then
    echo "⚠️  Docker daemon is not running"
    echo "   Please start Docker Desktop and try again"
    echo "   Or run without Docker services (some features may not work)"
    echo ""
    read -p "Continue without Docker services? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Start Docker Desktop and run the script again."
        exit 1
    fi
else
    docker compose -f docker-compose.services.yml up -d
fi

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check services
echo "✅ Checking services..."
docker compose -f docker-compose.services.yml ps

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8000 is already in use"
    
    # Try multiple methods to find and stop Docker containers
    DOCKER_CONTAINER=""
    
    # Method 1: Check by port mapping
    DOCKER_CONTAINER=$(docker ps --filter "publish=8000" --format "{{.Names}}" 2>/dev/null | head -1)
    
    # Method 2: Check by container name
    if [ -z "$DOCKER_CONTAINER" ]; then
        DOCKER_CONTAINER=$(docker ps --filter "name=claricare-backend" --format "{{.Names}}" 2>/dev/null | head -1)
    fi
    
    # Method 3: Check all containers and find one using port 8000
    if [ -z "$DOCKER_CONTAINER" ]; then
        for container in $(docker ps --format "{{.Names}}" 2>/dev/null); do
            if docker port "$container" 2>/dev/null | grep -q ":8000"; then
                DOCKER_CONTAINER="$container"
                break
            fi
        done
    fi
    
    if [ ! -z "$DOCKER_CONTAINER" ]; then
        echo "   Found Docker container '$DOCKER_CONTAINER' using port 8000"
        echo "   Stopping Docker container to run natively..."
        docker stop "$DOCKER_CONTAINER" 2>/dev/null || true
        docker compose stop backend 2>/dev/null || true
        docker compose -f docker-compose.yml stop backend 2>/dev/null || true
        sleep 2
    else
        # Check if it's a Docker process (com.docker)
        DOCKER_PID=$(lsof -Pi :8000 -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ ! -z "$DOCKER_PID" ]; then
            PROCESS_NAME=$(ps -p "$DOCKER_PID" -o comm= 2>/dev/null 2>&1 || echo "")
            if echo "$PROCESS_NAME" | grep -qiE "docker|com\.docker" 2>/dev/null; then
                echo "   Found Docker process using port 8000"
                echo "   Stopping all Docker backend containers..."
                docker compose stop backend 2>/dev/null || true
                docker compose -f docker-compose.yml stop backend 2>/dev/null || true
                docker ps --filter "name=claricare-backend" -q | xargs docker stop 2>/dev/null || true
                sleep 2
            fi
        fi
    fi
    
    # Verify port is free, kill if still in use
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   Port still in use, freeing it..."
        lsof -ti :8000 | xargs kill -9 2>/dev/null || true
        sleep 1
        if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo "   ❌ Could not free port 8000"
            echo "   Please stop the process manually:"
            echo "   lsof -ti :8000 | xargs kill -9"
            exit 1
        fi
    fi
    echo "✅ Port 8000 is now free"
fi

# Run the backend
echo ""
echo "🚀 Starting NidanMitra AI backend with MPS acceleration..."
echo "   API Docs: http://localhost:8000/docs"
echo "   Health:   http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo "================================================"

# Run with reload, but exclude venv and other unnecessary directories
$PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "app/venv/*" --reload-exclude "*.pyc" --reload-exclude "__pycache__/*"

