"""
Vector Store Module
Handles ChromaDB operations and embeddings
"""

import os
import logging
import hashlib
import math
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# Avoid OpenMP duplicate runtime crashes on some Windows setups.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import chromadb
from chromadb.config import Settings

from langchain_community.vectorstores import Chroma

from config import config

logger = logging.getLogger(__name__)


class SimpleTextSplitter:
    """Fallback splitter when langchain splitters cannot be imported."""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = max(1, int(chunk_size))
        safe_overlap = max(0, int(chunk_overlap))
        self.chunk_overlap = min(safe_overlap, self.chunk_size - 1)

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        chunks: List[str] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunks.append(text[start:end])
            if end >= text_len:
                break
            start += step

        return chunks


class SimpleEmbeddingFunction:
    """Lightweight embedding fallback that avoids external model dependencies."""

    def __init__(self, dim: int = 384):
        self.dim = max(8, int(dim))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        vec = [0.0] * self.dim
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            vec[idx] += 1.0

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec


def _resolve_text_splitter():
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        return RecursiveCharacterTextSplitter
    except Exception as exc:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            return RecursiveCharacterTextSplitter
        except Exception as inner_exc:
            logger.warning(
                "Falling back to SimpleTextSplitter (text splitter import failed): %s",
                inner_exc,
            )
            return None


def _resolve_embeddings_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings
    except Exception:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings
        except Exception:
            try:
                from langchain.embeddings import HuggingFaceEmbeddings
                return HuggingFaceEmbeddings
            except Exception as exc:
                raise RuntimeError(
                    "Unable to import HuggingFaceEmbeddings. "
                    "Check langchain/transformers dependencies."
                ) from exc


class VectorStore:
    """Manage vector database operations"""
    
    def __init__(self, lazy_init: bool = False):
        self.embeddings = None
        self.vector_store = None
        self._initialized = False
        splitter_cls = _resolve_text_splitter()
        if splitter_cls is None:
            self.text_splitter = SimpleTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
            )
        else:
            self.text_splitter = splitter_cls(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                length_function=len,
            )
        if not lazy_init:
            self._initialize_store()
            logger.info("VectorStore initialized")
        else:
            logger.info("VectorStore initialized (lazy)")
    
    def _initialize_store(self):
        """Initialize embeddings and vector store"""
        try:
            # Initialize embeddings
            try:
                embeddings_cls = _resolve_embeddings_class()
                self.embeddings = embeddings_cls(
                    model_name=config.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                logger.info(f"Loaded embedding model: {config.EMBEDDING_MODEL}")
            except Exception as exc:
                logger.warning(
                    "Falling back to SimpleEmbeddingFunction: %s",
                    exc,
                )
                self.embeddings = SimpleEmbeddingFunction()
            
            # Initialize ChromaDB
            self.vector_store = Chroma(
                collection_name=config.COLLECTION_NAME,
                embedding_function=self.embeddings,
                persist_directory=str(config.CHROMA_PERSIST_DIR)
            )
            logger.info(f"ChromaDB initialized at: {config.CHROMA_PERSIST_DIR}")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise

    def _ensure_initialized(self):
        """Ensure embeddings and vector store are ready before use."""
        if not self._initialized:
            self._initialize_store()
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add documents to vector store
        
        Args:
            documents: List of document dictionaries with 'text' and metadata
            
        Returns:
            List of document IDs
        """
        try:
            self._ensure_initialized()
            all_chunks = []
            all_metadatas = []
            
            for doc in documents:
                text = doc.get("text", "")
                if not text or not text.strip():
                    logger.warning("Skipping empty document: %s", doc.get("source", "unknown"))
                    continue

                # Split text into chunks
                text_chunks = self.text_splitter.split_text(text)
                
                # Create metadata for each chunk
                metadata = {
                    'source': doc.get('source', 'unknown'),
                    'type': doc.get('type', 'unknown'),
                    'num_pages': doc.get('num_pages', 0)
                }
                
                for i, chunk in enumerate(text_chunks):
                    all_chunks.append(chunk)
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_index'] = i
                    all_metadatas.append(chunk_metadata)

            if not all_chunks:
                logger.warning("No non-empty text chunks to add to the vector store.")
                return []
            
            # Add to vector store
            ids = self.vector_store.add_texts(
                texts=all_chunks,
                metadatas=all_metadatas
            )
            
            logger.info(f"Added {len(all_chunks)} chunks to vector store")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            self._ensure_initialized()
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': float(score)
                })
            
            logger.info(f"Found {len(formatted_results)} relevant documents")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise
    
    def clear_collection(self):
        """Clear all documents from the collection"""
        try:
            self._ensure_initialized()
            self.vector_store.delete_collection()
            self.embeddings = None
            self.vector_store = None
            self._initialized = False
            self._initialize_store()
            logger.info("Collection cleared and reinitialized")
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            if self.vector_store is not None:
                collection = self.vector_store._collection
            else:
                settings = Settings(
                    is_persistent=True,
                    persist_directory=str(config.CHROMA_PERSIST_DIR)
                )
                client = chromadb.Client(settings)
                collection = client.get_or_create_collection(config.COLLECTION_NAME)
            count = collection.count()
            
            return {
                'total_documents': count,
                'collection_name': config.COLLECTION_NAME
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {'total_documents': 0, 'collection_name': config.COLLECTION_NAME}
