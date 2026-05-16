from __future__ import annotations

from fastapi import APIRouter

from app.core.config import COLLECTION_NAME, EMBEDDING_MODEL, PDF_DIR
from app.services.state import load_state

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check():
    state = load_state()
    file_count = len(state.get("files", {}))
    return {
        "status": "ok",
        "pdf_dir": str(PDF_DIR),
        "indexed_files": file_count,
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "watching": True,
    }
