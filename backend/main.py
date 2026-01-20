"""
FastAPI backend entrypoint (v2).
Keeps startup light and loads heavy models lazily on demand.
"""

from functools import lru_cache
import logging
from pathlib import Path
import threading
from typing import List, Optional, TYPE_CHECKING

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import config

if TYPE_CHECKING:
    from agents.multimodal_agent import MultimodalAgent
    from utils.audio_processor import AudioProcessor


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multimodal Vox Agent API v2", version="2.0.0")

WRITE_LOCK = threading.Lock()
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif"
}
MAX_FILE_SIZE = 50 * 1024 * 1024


class QueryRequest(BaseModel):
    query: str


class TTSRequest(BaseModel):
    text: str


@lru_cache(maxsize=1)
def get_agent() -> "MultimodalAgent":
    from agents.multimodal_agent import MultimodalAgent
    return MultimodalAgent()


@lru_cache(maxsize=1)
def get_audio_processor() -> "AudioProcessor":
    from utils.audio_processor import AudioProcessor
    return AudioProcessor()


def _validate_upload(filename: str) -> Optional[str]:
    if not filename:
        return "invalid file name"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return f"unsupported type ({suffix})"
    if suffix == ".doc":
        return "legacy .doc is not supported"
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    agent = get_agent()
    return agent.vector_store.get_collection_stats()


@app.post("/clear")
def clear_collection():
    agent = get_agent()
    with WRITE_LOCK:
        agent.vector_store.clear_collection()
    return {"status": "cleared"}


@app.post("/process")
async def process_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_paths = []
    skipped = []

    for uploaded_file in files:
        reason = _validate_upload(uploaded_file.filename)
        if reason:
            skipped.append(f"{uploaded_file.filename} ({reason})")
            continue

        data = await uploaded_file.read()
        if len(data) > MAX_FILE_SIZE:
            skipped.append(f"{uploaded_file.filename} (file too large, max 50MB)")
            continue

        file_path = config.UPLOAD_DIR / uploaded_file.filename
        file_path.write_bytes(data)
        file_paths.append(str(file_path))

    if not file_paths:
        return {
            "success": 0,
            "failed": 0,
            "errors": [],
            "processed_files": [],
            "skipped": skipped
        }

    agent = get_agent()
    with WRITE_LOCK:
        result = agent.process_documents(file_paths)

    result["skipped"] = skipped
    return result


@app.post("/query")
def query(request: QueryRequest):
    query_text = request.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query is empty.")

    agent = get_agent()
    return agent.query(query_text)


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    audio_path = config.TEMP_DIR / file.filename
    audio_path.write_bytes(data)

    processor = get_audio_processor()
    text = processor.transcribe_audio(audio_path)
    return {"text": text}


@app.post("/tts")
def text_to_speech(request: TTSRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty.")

    try:
        processor = get_audio_processor()
        audio_path = processor.text_to_speech(text)
        return FileResponse(
            path=audio_path,
            media_type="audio/wav",
            filename=audio_path.name
        )
    except ValueError as e:
        # TTS not configured or other validation error
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Text-to-Speech failed: {str(e)}"
        )
