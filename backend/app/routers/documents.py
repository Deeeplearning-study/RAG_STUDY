from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile

from app.core.config import PDF_DIR
from app.core.pdf_utils import sanitize_filename
from app.schemas import DocumentInfo, DocumentsResponse
from app.services.ingestion import ingest_pdf, sync_pdf_folder
from app.services.state import load_state

router = APIRouter(tags=["documents"])


@router.get("/api/documents", response_model=DocumentsResponse)
def list_documents():
    state = load_state()
    items = []
    for source_path, info in sorted(state.get("files", {}).items(), key=lambda item: item[1].get("filename", "")):
        items.append(
            DocumentInfo(
                filename=info.get("filename", ""),
                source_path=source_path,
                pages=info.get("pages", 0),
                chunks=info.get("chunks", 0),
                indexed_at=info.get("indexed_at", 0.0),
            )
        )
    return DocumentsResponse(documents=items, count=len(items))


@router.post("/api/scan")
def scan_now():
    return sync_pdf_folder()


@router.post("/api/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    uploaded = []
    skipped = []
    indexed = 0

    for upload in files:
        if not upload.filename:
            continue
        if not upload.filename.lower().endswith(".pdf"):
            skipped.append(upload.filename)
            continue

        safe_name = sanitize_filename(upload.filename)
        target = PDF_DIR / safe_name
        if target.exists():
            stem = target.stem
            suffix = target.suffix
            counter = 2
            while True:
                candidate = PDF_DIR / f"{stem}-{counter}{suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                counter += 1

        content = await upload.read()
        target.write_bytes(content)
        result = ingest_pdf(target)
        uploaded.append(target.name)
        if result.get("skipped"):
            skipped.append(target.name)
        else:
            indexed += int(result.get("indexed", 0))

    return {"uploaded": uploaded, "indexed": indexed, "skipped": skipped}
