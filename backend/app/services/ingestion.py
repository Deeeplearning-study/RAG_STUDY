from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from app.core.chroma import get_collection, get_model
from app.core.config import PDF_DIR, SCAN_INTERVAL_SECONDS
from app.core.pdf_utils import chunk_text, extract_pdf_pages, file_digest
from app.services.state import load_state, save_state

_scan_started = False
_collection = get_collection()


def delete_existing_chunks(source_path: str) -> None:
    try:
        _collection.delete(where={"source_path": source_path})
    except Exception:
        pass


def ingest_pdf(pdf_path: Path) -> Dict[str, Any]:
    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))
    if pdf_path.suffix.lower() != ".pdf":
        return {"filename": pdf_path.name, "indexed": 0, "skipped": True, "reason": "not_pdf"}

    source_path = str(pdf_path.resolve())
    digest = file_digest(pdf_path)
    state = load_state()
    files_state = state.setdefault("files", {})
    previous = files_state.get(source_path)
    if previous and previous.get("sha256") == digest:
        return {"filename": pdf_path.name, "indexed": 0, "skipped": True, "reason": "unchanged"}

    pages = extract_pdf_pages(pdf_path)
    if not pages:
        return {"filename": pdf_path.name, "indexed": 0, "skipped": True, "reason": "no_text"}

    delete_existing_chunks(source_path)

    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    ids: List[str] = []

    for page_item in pages:
        page = page_item["page"]
        chunks = chunk_text(page_item["text"])
        for chunk_index, chunk in enumerate(chunks, start=1):
            documents.append(chunk)
            metadatas.append(
                {
                    "title": pdf_path.stem,
                    "filename": pdf_path.name,
                    "source_path": source_path,
                    "page": page,
                    "chunk_index": chunk_index,
                    "chunk_count": len(chunks),
                    "sha256": digest,
                }
            )
            ids.append(f"{digest[:12]}-p{page}-c{chunk_index}")

    if not documents:
        return {"filename": pdf_path.name, "indexed": 0, "skipped": True, "reason": "empty_chunks"}

    embeddings = get_model().encode(
        documents,
        batch_size=min(32, max(1, len(documents))),
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    _collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    files_state[source_path] = {
        "filename": pdf_path.name,
        "sha256": digest,
        "indexed_at": time.time(),
        "pages": len(pages),
        "chunks": len(documents),
    }
    save_state(state)

    return {"filename": pdf_path.name, "indexed": len(documents), "skipped": False, "pages": len(pages)}


def sync_pdf_folder() -> Dict[str, Any]:
    state = load_state()
    files_state = state.setdefault("files", {})
    current_files = {str(path.resolve()): path for path in PDF_DIR.rglob("*.pdf") if path.is_file()}

    removed = []
    for indexed_path in list(files_state.keys()):
        if indexed_path not in current_files:
            delete_existing_chunks(indexed_path)
            removed.append(indexed_path)
            del files_state[indexed_path]

    indexed = []
    skipped = []
    for path in sorted(current_files.values(), key=lambda item: item.name.lower()):
        result = ingest_pdf(path)
        if result.get("skipped"):
            skipped.append(result["filename"])
        else:
            indexed.append(result["filename"])

    save_state(state)
    return {"indexed": indexed, "skipped": skipped, "removed": removed}


def start_folder_watcher() -> None:
    global _scan_started
    if _scan_started:
        return
    _scan_started = True

    def loop() -> None:
        while True:
            try:
                sync_pdf_folder()
            except Exception:
                pass
            time.sleep(SCAN_INTERVAL_SECONDS)

    thread = threading.Thread(target=loop, daemon=True, name="pdf-folder-watcher")
    thread.start()
