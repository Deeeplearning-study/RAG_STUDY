from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
PDF_DIR = ROOT_DIR / "pdf"
BACKEND_DIR = ROOT_DIR / "backend"
CHROMA_DIR = BACKEND_DIR / "chroma_db"
STATE_FILE = BACKEND_DIR / "index_state.json"
COLLECTION_NAME = "rag_study_docs"
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "jhgan/ko-sroberta-multitask",
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
SCAN_INTERVAL_SECONDS = int(os.getenv("PDF_SCAN_INTERVAL", "10"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))

PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
