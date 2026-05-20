from __future__ import annotations

import threading
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from .config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
_model: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()


def get_collection():
    return _collection


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model
