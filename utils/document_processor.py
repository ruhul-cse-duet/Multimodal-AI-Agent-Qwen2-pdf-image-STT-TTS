"""
Document Processor Module
Handles PDF, DOCX, and Image processing with error handling
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

# Avoid OpenMP duplicate runtime crashes on some Windows setups.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from pypdf import PdfReader
from docx import Document
from PIL import Image
import pytesseract

from config import config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process various document types"""
    
    def __init__(self):
        self.easyocr_reader = None
        self.captioner = None
        logger.info("DocumentProcessor initialized")
    
    def _get_easyocr_reader(self):
        """Lazy load EasyOCR reader"""
        if self.easyocr_reader is None:
            try:
                import easyocr
                self.easyocr_reader = easyocr.Reader(['en', 'bn'])
                logger.info("EasyOCR reader initialized")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {str(e)}")
                raise
        return self.easyocr_reader
    
    def process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """
        Process PDF file and extract text
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            reader = PdfReader(str(file_path))
            text_content = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        text_content.append(f"[Page {page_num}]\n{text.strip()}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                    continue

            result = {
                "text": "\n\n".join(text_content).strip(),
                "num_pages": len(reader.pages),
                "type": "pdf",
                "source": str(file_path)
            }

            logger.info(f"Successfully processed PDF: {file_path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def process_docx(self, file_path: Path) -> Dict[str, Any]:
        """
        Process DOCX file and extract text

        Args:
            file_path: Path to DOCX file

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            doc = Document(str(file_path))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]

            result = {
                "text": "\n\n".join(paragraphs),
                "num_paragraphs": len(paragraphs),
                "type": "docx",
                "source": str(file_path)
            }

            logger.info(f"Successfully processed DOCX: {file_path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {str(e)}")
            raise ValueError(f"Failed to process DOCX: {str(e)}")
    
    def _get_captioner(self):
        """Lazy load image captioning model"""
        if self.captioner is None:
            try:
                from transformers import pipeline
                self.captioner = pipeline("image-to-text", model=config.VISION_MODEL)
                logger.info(f"Loaded vision model: {config.VISION_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize vision model: {str(e)}")
                raise
        return self.captioner

    def process_image(
        self,
        file_path: Path,
        use_easyocr: bool = True,
        use_caption: bool = True
    ) -> Dict[str, Any]:
        """
        Process image and extract text using OCR
        
        Args:
            file_path: Path to image file
            use_easyocr: Whether to use EasyOCR (supports Bengali)
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            image = Image.open(file_path)

            # Try EasyOCR first (supports multiple languages)
            ocr_text = ""
            if use_easyocr:
                try:
                    reader = self._get_easyocr_reader()
                    results = reader.readtext(str(file_path))
                    ocr_text = " ".join([result[1] for result in results])
                    logger.info(f"EasyOCR extracted {len(results)} text regions")
                except Exception as e:
                    logger.warning(f"EasyOCR failed, falling back to Tesseract: {str(e)}")

            # Fallback to Tesseract
            if not ocr_text:
                ocr_text = pytesseract.image_to_string(image).strip()

            caption_text = ""
            if use_caption:
                try:
                    captioner = self._get_captioner()
                    captions = captioner(image)
                    if captions:
                        caption_text = captions[0].get("generated_text", "").strip()
                except Exception as e:
                    logger.warning(f"Image captioning failed: {str(e)}")

            text_parts = []
            if ocr_text:
                text_parts.append(f"OCR:\n{ocr_text}")
            if caption_text:
                text_parts.append(f"Caption:\n{caption_text}")

            result = {
                "text": "\n\n".join(text_parts).strip(),
                "image_size": image.size,
                "image_mode": image.mode,
                "type": "image",
                "source": str(file_path)
            }

            logger.info(f"Successfully processed image: {file_path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def process_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Process document based on file type
        
        Args:
            file_path: Path to document
            
        Returns:
            Dictionary with extracted content
        """
        suffix = file_path.suffix.lower()
        
        try:
            if suffix == '.pdf':
                return self.process_pdf(file_path)
            elif suffix == '.docx':
                return self.process_docx(file_path)
            elif suffix == '.doc':
                raise ValueError("Legacy .doc format is not supported. Please convert to .docx.")
            elif suffix in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
                return self.process_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
                
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}")
            raise
