from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


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


class DocumentInfo(BaseModel):
    filename: str
    source_path: str
    pages: int
    chunks: int
    indexed_at: float


class DocumentsResponse(BaseModel):
    documents: List[DocumentInfo]
    count: int
