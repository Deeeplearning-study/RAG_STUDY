from __future__ import annotations

from typing import List

from app.core.chroma import get_collection, get_model
from app.core.config import ENABLE_RERANKER, RERANK_CANDIDATES
from app.schemas import ChatSource
from app.services.reranking import rerank_documents

_collection = get_collection()


def retrieve_sources(question: str, top_k: int) -> List[ChatSource]:
    question = question.strip()
    if not question:
        return []

    question_embedding = get_model().encode(
        [question], normalize_embeddings=True, show_progress_bar=False
    ).tolist()[0]
    results = _collection.query(
        query_embeddings=[question_embedding],
        n_results=max(top_k, RERANK_CANDIDATES) if ENABLE_RERANKER else top_k,
        include=["documents", "metadatas", "distances"],
    )

    sources: List[ChatSource] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    rows = list(zip(documents, metadatas, distances))
    score_is_rerank = False
    if ENABLE_RERANKER and rows:
        try:
            ranked = rerank_documents(question, [str(document) for document, _, _ in rows])
            rows = [(rows[idx][0], rows[idx][1], score) for idx, score in ranked[:top_k]]
            score_is_rerank = True
        except Exception:
            rows = rows[:top_k]
    else:
        rows = rows[:top_k]

    for idx, (document, metadata, score_value) in enumerate(rows, start=1):
        if metadata is None:
            metadata = {}
        if score_is_rerank:
            score = float(score_value or 0.0)
        else:
            score = max(0.0, 1.0 - float(score_value or 0.0))
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
