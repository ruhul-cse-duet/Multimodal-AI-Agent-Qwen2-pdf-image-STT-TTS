"""
Configuration Management Module
Handles environment variables and application settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Application configuration class"""
    
    # Base Paths
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
    TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "temp")
    CHROMA_PERSIST_DIR = BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    
    # LLM Configuration
    LLM_STUDIO_API_KEY = os.getenv("LLM_STUDIO_API_KEY", "")
    LLM_STUDIO_BASE_URL = os.getenv("LLM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "liquid/lfm2-1.2b")
    
    # Model Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    VISION_MODEL = os.getenv("VISION_MODEL", "qwen/qwen3-vl-4b")
    FORCE_TEXT_ONLY = os.getenv("FORCE_TEXT_ONLY", "False").lower() == "true"
    
    # Audio Configuration
    STT_MODEL = os.getenv("STT_MODEL", "base")
    STT_LANGUAGE = os.getenv("STT_LANGUAGE", "")
    TTS_MODEL = os.getenv("TTS_MODEL", "en_US-lessac-medium")
    AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    PIPER_BINARY = os.getenv("PIPER_BINARY", "piper")
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "")
    PIPER_CONFIG_PATH = os.getenv("PIPER_CONFIG_PATH", "")
    PIPER_SPEAKER_ID = os.getenv("PIPER_SPEAKER_ID", "")
    
    # Vector Store Configuration
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "multimodal_docs")
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # Agent Configuration
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
    AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "True").lower() == "true"
    MAX_IMAGE_CONTEXT = int(os.getenv("MAX_IMAGE_CONTEXT", "2"))
    
    # Application Settings
    APP_TITLE = os.getenv("APP_TITLE", "Multimodal Vox Agent AI")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        for directory in [cls.UPLOAD_DIR, cls.TEMP_DIR, cls.CHROMA_PERSIST_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate critical configuration"""
        try:
            cls.ensure_directories()
            logger.info("Configuration validated successfully")
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False


# Initialize configuration on import
config = Config()
config.ensure_directories()
