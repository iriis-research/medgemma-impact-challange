"""
Test endpoint to verify backend is accessible
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    """Simple ping endpoint to test connectivity."""
    return {
        "status": "ok",
        "message": "Backend is running and accessible",
        "endpoint": "/api/test/ping"
    }

@router.post("/echo")
async def echo(data: dict):
    """Echo endpoint to test POST requests."""
    return {
        "status": "ok",
        "received": data,
        "message": "Backend received your data"
    }
