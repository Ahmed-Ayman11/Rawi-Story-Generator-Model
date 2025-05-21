"""
راوي (Rawi) - Arabic AI Storytelling Platform
Main application file for FastAPI server
"""

import os
import sys
import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Add the current directory to Python path to enable imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import application routers
from routers import story

# ======== Configure Logging ========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== Load Environment Variables ========
load_dotenv()

# ======== Server Configuration ========
HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
PORT = int(os.getenv("BACKEND_PORT", "7860"))  # Updated default port for Hugging Face
BASE_URL = os.getenv("BASE_URL", f"http://{HOST}:{PORT}")
AUDIO_STORAGE_PATH = os.path.abspath(os.getenv("AUDIO_STORAGE_PATH", "./audio_files"))

# DeepSeek API Key check
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Log server settings
logger.info(f"Server settings:")
logger.info(f"Host: {HOST}")
logger.info(f"Port: {PORT}")
logger.info(f"Base URL: {BASE_URL}")
logger.info(f"Audio storage path: {AUDIO_STORAGE_PATH}")
logger.info(f"DeepSeek API Key set: {bool(DEEPSEEK_API_KEY)}")

# ======== Ensure Audio Storage Directory Exists ========
try:
    Path(AUDIO_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    logger.info(f"Created/verified audio storage directory at: {AUDIO_STORAGE_PATH}")
except Exception as e:
    logger.error(f"Error creating audio storage directory: {str(e)}")
    raise

# ======== Initialize FastAPI Application ========
app = FastAPI(
    title="راوي API",
    description="واجهة برمجة تطبيقات لمنصة راوي لتوليد القصص العربية باستخدام الذكاء الاصطناعي",
    version="1.0.0"
)

# ======== Configure CORS ========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== Mount Static Files ========
app.mount("/audio", StaticFiles(directory=AUDIO_STORAGE_PATH), name="audio")

# ======== Register Routers ========
app.include_router(story.router, prefix="/api/stories", tags=["قصص"])

# ======== API Endpoints ========
@app.get("/", tags=["الرئيسية"])
async def root():
    """
    Root endpoint for the API
    """
    return {
        "message": "مرحباً بك في واجهة برمجة تطبيقات راوي",
        "docs": f"{BASE_URL}/docs"
    }

@app.get("/health", tags=["الحالة"])
async def health_check():
    """
    Health check endpoint to verify API configuration
    """
    health_status = {
        "status": "healthy",
        "deepseek_api": bool(DEEPSEEK_API_KEY),
        "audio_storage": os.path.exists(AUDIO_STORAGE_PATH),
    }
    
    if not DEEPSEEK_API_KEY:
        health_status["status"] = "degraded"
        health_status["message"] = "DeepSeek API key is not set. Story generation will not work."
        
    return health_status

# ======== Run Application ========
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True  # Disable in production for better performance
    )