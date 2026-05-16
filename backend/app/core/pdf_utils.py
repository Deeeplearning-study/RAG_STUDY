from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List

from pypdf import PdfReader


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9가-힣._ -]+", "_", name).strip()
    return name or "document.pdf"


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 1100, overlap: int = 180) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: List[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        piece = current.strip()
        if piece:
            chunks.append(piece)
        current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            flush_current()
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + max_chars)
                chunks.append(paragraph[start:end].strip())
                if end >= len(paragraph):
                    break
                start = max(0, end - overlap)
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            flush_current()
            current = paragraph

    flush_current()

    if overlap > 0 and len(chunks) > 1:
        overlapped: List[str] = []
        previous_tail = ""
        for chunk in chunks:
            merged = f"{previous_tail}\n\n{chunk}".strip() if previous_tail else chunk
            overlapped.append(merged[: max_chars + overlap])
            previous_tail = chunk[-overlap:]
        chunks = overlapped

    return [chunk.strip() for chunk in chunks if chunk.strip()]


def extract_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    pages: List[Dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = normalize_text(text)
        if text:
            pages.append({"page": page_number, "text": text})
    return pages
