from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path, encoding: str = "utf-8") -> Any:
    return json.loads(Path(path).read_text(encoding=encoding))


def write_json(path: str | Path, obj: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")
