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


import tempfile
from pathlib import Path


def save_state(state: Dict[str, Any]) -> None:
    temp_dir = STATE_FILE.parent
    try:
        with tempfile.NamedTemporaryFile('w', dir=temp_dir, delete=False, encoding='utf-8', suffix='.tmp') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            temp_name = f.name
        Path(temp_name).replace(STATE_FILE)
    except Exception:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
