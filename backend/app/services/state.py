from __future__ import annotations

import json
from typing import Any, Dict

from app.core.config import STATE_FILE


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"files": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
