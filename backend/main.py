from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request

import chromadb
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

ROOT_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT_DIR / "pdf"
CHROMA_DIR = ROOT_DIR / "backend" / "chroma_db"
STATE_FILE = ROOT_DIR / "backend" / "index_state.json"
COLLECTION_NAME = "rag_study_docs"
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
SCAN_INTERVAL_SECONDS = int(os.getenv("PDF_SCAN_INTERVAL", "10"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))

PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RAG Study Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
_model: Optional[SentenceTransformer] = None
_model_lock = threading.Lock()
_state_lock = threading.Lock()
_scan_started = False


class ChatRequest(BaseModel):
    message: str
    top_k: Optional[int] = None


class ChatSource(BaseModel):
    title: str
    source_path: str
    page: Optional[int] = None
    chunk_index: int
    score: float
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
    retrieved_count: int
    model: str


class UploadResponse(BaseModel):
    uploaded: List[str]
    indexed: int
    skipped: List[str]


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"files": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9가-힣._ -]+", "_", name).strip()
    return name or f"document-{int(time.time())}.pdf"


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

    return {
        "filename": pdf_path.name,
        "indexed": len(documents),
        "skipped": False,
        "pages": len(pages),
    }


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


def retrieve_sources(question: str, top_k: int) -> List[ChatSource]:
    question = question.strip()
    if not question:
        return []

    question_embedding = get_model().encode(
        [question], normalize_embeddings=True, show_progress_bar=False
    ).tolist()[0]
    results = _collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    sources: List[ChatSource] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for idx, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        score = max(0.0, 1.0 - float(distance or 0.0))
        sources.append(
            ChatSource(
                title=str(metadata.get("title") or metadata.get("filename") or "document"),
                source_path=str(metadata.get("source_path") or ""),
                page=metadata.get("page"),
                chunk_index=int(metadata.get("chunk_index") or idx),
                score=round(score, 4),
                snippet=str(document).strip(),
            )
        )

    return sources


def build_prompt(question: str, sources: List[ChatSource]) -> str:
    source_lines = []
    for i, source in enumerate(sources, start=1):
        page_label = f", p.{source.page}" if source.page else ""
        source_lines.append(f"[{i}] {source.title}{page_label}: {source.snippet}")

    context = "\n\n".join(source_lines) if source_lines else "(관련 문서를 찾지 못했습니다.)"
    return f"""당신은 PDF 문서 기반 RAG 어시스턴트입니다.
반드시 아래 컨텍스트에 근거해서만 답변하세요.
컨텍스트에 없는 내용은 추측하지 말고, 모르면 모른다고 말하세요.
답변 끝에는 사용한 출처 번호를 간단히 붙이세요.

[컨텍스트]
{context}

[질문]
{question}
"""


def ask_ollama(question: str, sources: List[ChatSource]) -> Optional[str]:
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None

    prompt = build_prompt(question, sources)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You answer only from the provided context and cite sources."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    try:
        req = request.Request(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("message", {}).get("content") or data.get("response")
    except Exception:
        return None


def fallback_answer(question: str, sources: List[ChatSource]) -> str:
    if not sources:
        return (
            "관련 문서를 찾지 못했어요. PDF를 /pdf 폴더에 넣거나 프론트에서 업로드한 뒤 다시 질문해 주세요."
        )

    bullets = []
    for source in sources[:3]:
        page_label = f" p.{source.page}" if source.page else ""
        bullets.append(f"- {source.title}{page_label}: {source.snippet[:220]}")

    return (
        "아직 LLM 연결 전이라, 검색된 문서 조각을 바탕으로 우선 정리한 결과예요.\n\n"
        + "\n".join(bullets)
        + "\n\n원하면 이 자리에 Ollama(Gemma) 응답을 붙이도록 바꿀 수 있어요."
    )


@app.on_event("startup")
def startup_event() -> None:
    sync_pdf_folder()
    start_folder_watcher()


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


@app.get("/")
def read_root() -> Dict[str, Any]:
    return {
        "message": "RAG Study backend is running",
        "pdf_dir": str(PDF_DIR),
        "vector_db": str(CHROMA_DIR),
    }


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
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


@app.get("/api/documents")
def list_documents() -> Dict[str, Any]:
    state = load_state()
    items = []
    for source_path, info in sorted(state.get("files", {}).items(), key=lambda item: item[1].get("filename", "")):
        items.append(
            {
                "filename": info.get("filename"),
                "source_path": source_path,
                "pages": info.get("pages", 0),
                "chunks": info.get("chunks", 0),
                "indexed_at": info.get("indexed_at"),
            }
        )
    return {"documents": items, "count": len(items)}


@app.post("/api/scan")
def scan_now() -> Dict[str, Any]:
    return sync_pdf_folder()


@app.post("/api/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    uploaded: List[str] = []
    skipped: List[str] = []
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(request_body: ChatRequest) -> ChatResponse:
    top_k = request_body.top_k or TOP_K
    sources = retrieve_sources(request_body.message, top_k=top_k)
    ollama_answer = ask_ollama(request_body.message, sources)
    answer = ollama_answer or fallback_answer(request_body.message, sources)
    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieved_count=len(sources),
        model=OLLAMA_MODEL if ollama_answer else "fallback-context",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
