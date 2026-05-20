from __future__ import annotations

from fastapi import APIRouter

from app.core.config import TOP_K
from app.schemas import ChatRequest, ChatResponse
from app.services.ollama import ask_ollama
from app.services.retrieval import retrieve_sources

router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=ChatResponse)
def chat(request_body: ChatRequest) -> ChatResponse:
    top_k = request_body.top_k or TOP_K
    sources = retrieve_sources(request_body.message, top_k=top_k)
    ollama_answer = ask_ollama(request_body.message, sources)
    if ollama_answer:
        answer = ollama_answer
        model_name = "ollama"
    else:
        if not sources:
            answer = "관련 문서를 찾지 못했어요. PDF를 /pdf 폴더에 넣거나 프론트에서 업로드한 뒤 다시 질문해 주세요."
        else:
            bullets = []
            for source in sources[:3]:
                page_label = f" p.{source.page}" if source.page else ""
                bullets.append(f"- {source.title}{page_label}: {source.snippet[:220]}")
            answer = (
                "아직 LLM 연결 전이라, 검색된 문서 조각을 바탕으로 우선 정리한 결과예요.\n\n"
                + "\n".join(bullets)
                + "\n\n원하면 이 자리에 Ollama(Gemma) 응답을 붙이도록 바꿀 수 있어요."
            )
        model_name = "fallback-context"

    return ChatResponse(
        answer=answer,
        sources=sources,
        retrieved_count=len(sources),
        model=model_name,
    )
