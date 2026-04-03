from __future__ import annotations

import base64
from pathlib import Path


def infer_mime_type(image_path: str | Path) -> str:
    suffix = Path(image_path).suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return mapping.get(suffix, "image/jpeg")


def image_to_data_url(image_path: str | Path) -> str:
    image_path = Path(image_path)
    mime = infer_mime_type(image_path)
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"
