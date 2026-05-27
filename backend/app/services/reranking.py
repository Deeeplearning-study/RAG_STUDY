from __future__ import annotations

import threading
from typing import List, Tuple

from sentence_transformers import CrossEncoder

from app.core.config import RERANKER_MODEL

_reranker: CrossEncoder | None = None
_reranker_lock = threading.Lock()


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank_documents(question: str, documents: List[str]) -> List[Tuple[int, float]]:
    if not documents:
        return []

    pairs = [(question, document) for document in documents]
    scores = get_reranker().predict(pairs)
    ranked = [(idx, float(score)) for idx, score in enumerate(scores)]
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
