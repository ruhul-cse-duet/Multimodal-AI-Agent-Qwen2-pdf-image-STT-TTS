"""
Audio Processor Module
Handles Speech-to-Text and Text-to-Speech with error handling
Audio features are optional
"""

import logging
from pathlib import Path
from typing import Optional
import subprocess
import os

from config import config

logger = logging.getLogger(__name__)

# Optional import for faster_whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed. Audio transcription will not be available.")
    logger.warning("Install with: pip install faster-whisper")


class AudioProcessor:
    """Handle audio input/output operations"""
    
    def __init__(self):
        self.stt_model = None
        self.tts_available = self._check_tts_available()
        
        if not FASTER_WHISPER_AVAILABLE:
            logger.warning("AudioProcessor initialized without faster-whisper support")
        else:
            logger.info("AudioProcessor initialized")
        
        if not self.tts_available:
            logger.warning("Piper TTS not configured. Text-to-speech will not be available.")
    
    def _check_tts_available(self) -> bool:
        """Check if Piper TTS is properly configured"""
        if not config.PIPER_MODEL_PATH:
            logger.debug("PIPER_MODEL_PATH not set in .env")
            return False
        
        model_path = Path(config.PIPER_MODEL_PATH)
        if not model_path.exists():
            logger.debug(f"Piper model not found at: {model_path}")
            return False
        
        # Check if piper binary is available
        try:
            result = subprocess.run(
                [config.PIPER_BINARY, "--version"],
                capture_output=True,
                timeout=260
            )
            if result.returncode != 0:
                logger.debug("Piper binary not found or not working")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug("Piper binary not accessible")
            return False
        
        return True
    
    def _get_stt_model(self):
        """Lazy load Whisper model"""
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper is not installed. "
                "Install with: pip install faster-whisper"
            )
        
        if self.stt_model is None:
            try:
                self.stt_model = WhisperModel(
                    config.STT_MODEL,
                    device="cpu",
                    compute_type="int8"
                )
                logger.info(f"Whisper model '{config.STT_MODEL}' loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                raise
        return self.stt_model
    
    def transcribe_audio(self, audio_file: Path) -> str:
        """
        Transcribe audio file to text using Faster-Whisper
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcribed text
        """
        try:
            model = self._get_stt_model()
            
            language = config.STT_LANGUAGE or None
            segments, info = model.transcribe(
                str(audio_file),
                language=language,
                beam_size=5,
                vad_filter=True
            )
            
            transcription = " ".join([segment.text for segment in segments])
            
            logger.info(f"Transcribed audio: {audio_file.name} (detected language: {info.language})")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise ValueError(f"Failed to transcribe audio: {str(e)}")
    
    def text_to_speech(self, text: str, output_path: Optional[Path] = None) -> Path:
        """
        Convert text to speech using Piper TTS
        
        Args:
            text: Text to convert
            output_path: Output file path (optional)
            
        Returns:
            Path to generated audio file
            
        Raises:
            ValueError: If TTS is not configured or fails
        """
        if not text.strip():
            raise ValueError("No text provided for TTS.")
        
        if not self.tts_available:
            raise ValueError(
                "Text-to-Speech is not configured. "
                "To enable TTS:\n"
                "1. Download Piper TTS from: https://github.com/rhasspy/piper/releases\n"
                "2. Download a voice model from: https://github.com/rhasspy/piper/releases/tag/2023.11.14-2\n"
                "3. Set PIPER_MODEL_PATH in .env to the path of the voice model\n"
                "4. Optionally set PIPER_BINARY if piper is not in PATH\n"
                "\nAlternatively, use the text response without TTS."
            )
        
        try:
            model_path = Path(config.PIPER_MODEL_PATH)
            
            if output_path is None:
                output_path = config.TEMP_DIR / f"tts_{abs(hash(text))}.wav"

            command = [
                config.PIPER_BINARY,
                "--model",
                str(model_path),
                "--output_file",
                str(output_path)
            ]

            if config.PIPER_CONFIG_PATH:
                config_path = Path(config.PIPER_CONFIG_PATH)
                if config_path.exists():
                    command.extend(["--config", str(config_path)])
                    
            if config.PIPER_SPEAKER_ID:
                command.extend(["--speaker", str(config.PIPER_SPEAKER_ID)])

            result = subprocess.run(
                command,
                input=text,
                text=True,
                capture_output=True,
                check=False,
                timeout=300
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown Piper error."
                raise ValueError(f"Piper TTS failed: {error_msg}")

            logger.info(f"Generated TTS audio: {output_path.name}")
            return output_path

        except subprocess.TimeoutExpired:
            raise ValueError("TTS generation timed out (30 seconds)")
        except Exception as e:
            logger.error(f"Error in text-to-speech: {str(e)}")
            raise ValueError(f"Failed to generate speech: {str(e)}")
