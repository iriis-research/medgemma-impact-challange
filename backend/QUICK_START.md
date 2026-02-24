# Quick Start Guide

## ⚠️ Python 3.14 Compatibility Issue

Python 3.14 is too new and many packages don't support it yet. You have two options:

## Option 1: Use Docker (Recommended - Easiest)

Docker uses Python 3.11 which has full compatibility:

```bash
cd backend

# Create .env file
cat > .env << EOF
HF_TOKEN=your-huggingface-token-here
SECRET_KEY=your-super-secret-key
EOF

# Start all services
docker compose up -d

# View logs
docker compose logs -f backend
```

**That's it!** Backend will be available at `http://localhost:8000`

## Option 2: Use Python 3.11 or 3.12 (For Native Development)

### Install Python 3.11 or 3.12

**On macOS with Homebrew:**
```bash
brew install python@3.11
# or
brew install python@3.12
```

**On macOS with pyenv:**
```bash
pyenv install 3.11.9
# or
pyenv install 3.12.1
```

### Create venv with specific Python version

```bash
cd backend

# Remove old venv if it exists
rm -rf app/venv

# Create new venv with Python 3.11
python3.11 -m venv app/venv
# or
python3.12 -m venv app/venv

# Activate and install
source app/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Run the backend

```bash
# Start Docker services (PostgreSQL, Redis, Qdrant)
docker compose -f docker-compose.services.yml up -d

# Run backend
source app/venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Check Your Python Version

```bash
python3 --version
python3.11 --version  # Check if 3.11 is installed
python3.12 --version  # Check if 3.12 is installed
```

## Why Docker is Recommended

- ✅ No Python version issues
- ✅ All dependencies pre-configured
- ✅ Consistent environment
- ✅ Easy to start/stop
- ✅ Works on any system

## Troubleshooting

### "command not found: python3.11"
Install Python 3.11 first (see above).

### "Failed to build grpcio-tools"
You're using Python 3.14. Switch to Python 3.11/3.12 or use Docker.

### Port already in use
```bash
# Check what's using port 8000
lsof -i :8000

# Or change port in docker-compose.yml
```
