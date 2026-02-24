"""
NidanMitra - Patient Understanding & Adherence Companion
Main FastAPI Application
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import chat, reports, medications, symptoms, auth, test, dashboard
from app.db.database import init_db
from app.config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    # Initialize database (skip if not available in dev mode)
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization skipped: {e}")
        logger.info("Running without database - some features may be unavailable")
    
    # Check Ollama connection on startup
    try:
        from app.llm.medgemma_client import medgemma
        print(f"🏥 MedGemma configured via Ollama")
        print(f"   Model: {settings.ollama_model}")
        print(f"   URL: {settings.ollama_base_url}")
        logger.info(f"MedGemma configured via Ollama: {settings.ollama_model}")
        
        # Verify Ollama is running
        is_connected = await medgemma._check_ollama_connection()
        if is_connected:
            print("✅ Ollama connected and model available")
            logger.info("✅ Ollama connected and model available")
        else:
            print("⚠️  Ollama not connected or model not available")
            print("   Make sure 'ollama serve' is running")
            logger.warning("⚠️  Ollama not connected or model not available")
    except Exception as e:
        print(f"⚠️  Could not verify Ollama connection: {e}")
        logger.warning(f"⚠️  Could not verify Ollama connection: {e}")
    
    yield

app = FastAPI(
    title="NidanMitra",
    description="Patient Understanding & Adherence Companion API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# Allow localhost and ngrok origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1):\d+|https://.*\.ngrok-free\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(test.router, prefix="/api/test", tags=["Test"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(reports.router, prefix="/api/reports", tags=["Medical Reports"])
app.include_router(medications.router, prefix="/api/medications", tags=["Medications"])
app.include_router(symptoms.router, prefix="/api/symptoms", tags=["Symptom Journal"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Health Dashboard"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to NidanMitra",
        "description": "Patient Understanding & Adherence Companion",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    from app.llm.medgemma_client import medgemma
    return {
        "status": "healthy", 
        "service": "nidanmitra",
        "model": medgemma.get_model_info()
    }

