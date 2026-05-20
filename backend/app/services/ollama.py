from __future__ import annotations

import json
from typing import List, Optional
from urllib import request

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.schemas import ChatSource
from app.services.retrieval import build_prompt


def ask_ollama(question: str, sources: List[ChatSource]) -> Optional[str]:
    model = OLLAMA_MODEL
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
