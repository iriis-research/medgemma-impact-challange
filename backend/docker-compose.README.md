# Docker Setup Guide

## Overview

This Docker setup runs the complete ClariCare AI backend stack:
- **PostgreSQL** - Main database
- **Redis** - Caching and task queue
- **Qdrant** - Vector database for RAG features
- **Backend API** - FastAPI application

The frontend runs separately (not in Docker) for easier development.

## Quick Start

```bash
cd backend

# 1. Create .env file (optional)
cat > .env << EOF
HF_TOKEN=your-huggingface-token-here
SECRET_KEY=your-super-secret-key
EOF

# 2. Start all services
docker compose up -d

# 3. View logs
docker compose logs -f backend

# 4. Stop services
docker compose down
```

## Services

### PostgreSQL (Port 5432)
- Database: `claricare`
- User: `postgres`
- Password: `postgres`
- Data persisted in `postgres_data` volume

### Redis (Port 6379)
- Used for caching and Celery task queue
- Data persisted in `redis_data` volume

### Qdrant (Ports 6333, 6334)
- Vector database for RAG features
- Web UI: `http://localhost:6333/dashboard`
- Data persisted in `qdrant_data` volume

### Backend API (Port 8000)
- FastAPI application
- API Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Models cached in `models_data` volume
- Uploads stored in `uploads_data` volume

## Environment Variables

Key environment variables (set in `.env` or docker-compose.yml):

- `HF_TOKEN` - HuggingFace token (required for MedGemma)
- `SECRET_KEY` - JWT secret key
- `DEBUG` - Enable debug mode (default: false)
- `DEVICE` - Device for inference: cpu, cuda, mps (default: cpu)

## Volumes

All data is persisted in Docker volumes:
- `postgres_data` - Database data
- `redis_data` - Redis data
- `qdrant_data` - Vector database data
- `models_data` - Cached ML models
- `uploads_data` - User uploads

## Health Checks

All services include health checks and will wait for dependencies:
- Backend waits for PostgreSQL, Redis, and Qdrant
- Services start in the correct order automatically

## Troubleshooting

### View logs
```bash
docker compose logs -f [service-name]
```

### Restart a service
```bash
docker compose restart [service-name]
```

### Rebuild backend
```bash
docker compose build backend
docker compose up -d backend
```

### Clean start (removes all data)
```bash
docker compose down -v
docker compose up -d
```

### Access database
```bash
docker exec -it claricare-db psql -U postgres -d claricare
```

### Access Redis CLI
```bash
docker exec -it claricare-redis redis-cli
```
