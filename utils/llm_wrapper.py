"""
LLM Module
Handles interaction with Local LLM via LM Studio API
FIXED VERSION with proper VLM (Vision-Language Model) support
"""

import base64
import logging
import mimetypes
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests

from config import config

logger = logging.getLogger(__name__)


class LocalLLM:
    """Wrapper for Local LLM via LM Studio API with Vision Support"""
    
    def __init__(self):
        self.base_url = config.LLM_STUDIO_BASE_URL.rstrip('/')
        self.model = config.LOCAL_LLM_MODEL
        self.api_key = config.LLM_STUDIO_API_KEY
        self.force_text_only = getattr(config, "FORCE_TEXT_ONLY", False)
        
        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Check if model is a VLM
        self.is_vlm = self._check_if_vlm()
        logger.info(f"LocalLLM initialized with model: {self.model} (VLM: {self.is_vlm})")
    
    def _check_if_vlm(self) -> bool:
        """Check if the loaded model is a Vision-Language Model"""
        if self.force_text_only:
            return False

        model_lower = (self.model or "").lower()
        if not model_lower:
            return False

        if any(keyword in model_lower for keyword in ["qwen2-vl", "qwen3-vl", "llava", "minicpm", "pixtral"]):
            return True

        if "vision" in model_lower:
            return True

        return bool(re.search(r"(^|[^a-z0-9])vl([^a-z0-9]|$)", model_lower))
    
    def _check_connection(self) -> bool:
        """Check if LM Studio is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=300)
            if response.status_code == 200:
                models = response.json()
                logger.info(f"LM Studio connected. Available models: {models}")
                return True
            else:
                logger.warning(f"LM Studio responded with status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to LM Studio at {self.base_url}. Is it running?")
            return False
        except Exception as e:
            logger.error(f"Error checking LM Studio connection: {str(e)}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 250
    ) -> str:
        """
        Generate response from local LLM (text-only)
        
        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            if not self._check_connection():
                raise ConnectionError(
                    f"Cannot connect to LM Studio at {self.base_url}. "
                    "Please ensure LM Studio is running and a model is loaded."
                )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            logger.debug(f"Sending request to {self.base_url}/chat/completions")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=200
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' not in result or len(result['choices']) == 0:
                raise ValueError(f"Invalid response structure: {result}")
            
            generated_text = result['choices'][0]['message']['content']
            logger.info(f"✓ Generated response ({len(generated_text)} chars)")
            
            return generated_text
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    def _encode_image_for_api(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """
        Encode an image as a data URL for OpenAI-compatible API
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Image content part dict or None
        """
        try:
            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}")
                return None

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = "image/png"

            # Read and encode image
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            encoded = base64.b64encode(image_bytes).decode("ascii")
            data_url = f"data:{mime_type};base64,{encoded}"

            logger.debug(f"Encoded image: {image_path.name} ({len(encoded)} bytes)")
            
            return {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }
            
        except Exception as exc:
            logger.warning(f"Failed to encode image {image_path}: {exc}")
            return None

    def generate_multimodal(
        self,
        prompt: str,
        image_paths: List[Path],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 250
    ) -> str:
        """
        Generate response using text + images (multimodal)
        
        Args:
            prompt: Text prompt
            image_paths: List of image file paths
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            # Check if model supports vision
            if not self.is_vlm:
                logger.warning(
                    f"Model {self.model} may not support vision. "
                    f"Images will be ignored. Load a VLM model in LM Studio."
                )
                return self.generate(prompt, system_prompt, temperature, max_tokens)
            
            if not self._check_connection():
                raise ConnectionError(
                    f"Cannot connect to LM Studio at {self.base_url}. "
                    "Please ensure LM Studio is running with a VLM model loaded."
                )

            # Build content with text + images
            content_parts: List[Dict[str, Any]] = []
            
            # Add text first
            content_parts.append({"type": "text", "text": prompt})
            
            # Add images
            images_added = 0
            for image_path in image_paths:
                image_part = self._encode_image_for_api(Path(image_path))
                if image_part:
                    content_parts.append(image_part)
                    images_added += 1

            # If no images were successfully added, fall back to text-only
            if images_added == 0:
                logger.warning("No images could be encoded. Falling back to text-only generation.")
                return self.generate(prompt, system_prompt, temperature, max_tokens)

            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({
                "role": "user",
                "content": content_parts
            })

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            logger.debug(f"Sending multimodal request with {images_added} image(s)")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=200  # Longer timeout for vision models
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' not in result or len(result['choices']) == 0:
                raise ValueError(f"Invalid response structure: {result}")

            generated_text = result["choices"][0]["message"]["content"]
            logger.info(f"✓ Generated multimodal response ({len(generated_text)} chars, {images_added} images)")

            return generated_text

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"
            
            logger.error(error_msg)
            
            # Provide helpful error messages
            if e.response.status_code == 400:
                logger.error(
                    "This might mean the model doesn't support vision. "
                    "Falling back to text-only generation."
                )
                self.is_vlm = False
                return self.generate(prompt, system_prompt, temperature, max_tokens)
            
            raise
        except Exception as e:
            logger.error(f"Error generating multimodal response: {str(e)}")
            raise
    
    def generate_with_context(
        self,
        query: str,
        context: List[Dict[str, Any]],
        temperature: float = 0.7
    ) -> str:
        """
        Generate response with retrieved context
        
        Args:
            query: User query
            context: Retrieved context documents
            temperature: Sampling temperature
            
        Returns:
            Generated response
        """
        # Format context
        context_text = "\n\n".join([
            f"[Document {i+1} - {doc.get('metadata', {}).get('source', 'Unknown')}]\n{doc.get('content', '')}"
            for i, doc in enumerate(context)
        ])
        
        system_prompt = """You are a helpful AI assistant with expertise in analyzing documents. 
Use the provided context to answer questions accurately. If the answer cannot be found in the context, 
say so clearly. Always cite which document your answer comes from."""
        
        prompt = f"""Context Information:
{context_text}

User Question: {query}

Please provide a detailed and accurate answer based on the context above."""
        
        return self.generate(prompt, system_prompt, temperature)

    def generate_with_context_and_images(
        self,
        query: str,
        context: List[Dict[str, Any]],
        image_paths: List[Path],
        temperature: float = 0.7
    ) -> str:
        """
        Generate response with retrieved context and attached images (multimodal RAG)
        
        Args:
            query: User query
            context: Retrieved context documents
            image_paths: List of image paths to attach
            temperature: Sampling temperature
            
        Returns:
            Generated response
        """
        # Format context
        context_text = "\n\n".join([
            f"[Document {i+1} - {doc.get('metadata', {}).get('source', 'Unknown')}]\n{doc.get('content', '')}"
            for i, doc in enumerate(context)
        ])

        system_prompt = """You are a helpful AI assistant with expertise in analyzing documents and images.
Use the provided context and images to answer questions accurately. Analyze both the text context 
and the visual information in the images. If the answer cannot be found, say so clearly. 
Always cite which document or image your answer comes from."""

        prompt = f"""Context Information:
{context_text}

User Question: {query}

Please analyze the provided images along with the context above and provide a detailed answer."""

        return self.generate_multimodal(prompt, image_paths, system_prompt, temperature)
