from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

from src.utils.image_utils import image_to_data_url
from src.utils.time_utils import now_ms

def _extract_delta_text(value: Any) -> str:
    """兼容 str / list[dict] / list[str] 形式的流式文本块。"""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                # 常见 OpenAI / 兼容接口的文本块格式
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                    continue

                if isinstance(item.get("content"), str):
                    parts.append(item["content"])
                    continue

                # 某些实现里可能是 {"type": "...", "text": "..."}
                if item.get("type") in {"output_text", "text"} and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                    continue

        return "".join(parts)

    return ""

def build_messages(prompt_text: str, image_path: Optional[str] = None) -> List[Dict[str, Any]]:
    if not image_path:
        return [{"role": "user", "content": prompt_text}]
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
            ],
        }
    ]


def build_payload(
    model: str,
    prompt_text: str,
    *,
    image_path: Optional[str] = None,
    max_tokens: int = 128,
    temperature: float = 0.2,
    stream: bool = True,
    extra_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": build_messages(prompt_text, image_path),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }

    # 关键：让流式响应尽量把 usage 一起带回来
    # 如果服务端不支持，也不会影响主流程，只是 usage 可能还是 None
    if stream:
        payload["stream_options"] = {"include_usage": True}

    if extra_body:
        payload.update(extra_body)

    return payload


def http_json(url: str, payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def stream_chat_completion(api_url: str, payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    req = Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = now_ms()
    ttft_any_ms: Optional[float] = None
    ttft_answer_ms: Optional[float] = None

    reasoning_parts: List[str] = []
    answer_parts: List[str] = []
    final_obj: Optional[Dict[str, Any]] = None
    usage_obj: Optional[Dict[str, Any]] = None

    with urlopen(req, timeout=timeout) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue

            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break

            try:
                obj = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            final_obj = obj

            # 有些兼容实现会把 usage 放在最终 chunk
            if isinstance(obj.get("usage"), dict):
                usage_obj = obj["usage"]

            choice = (obj.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}

            reasoning_piece = _extract_delta_text(delta.get("reasoning_content"))
            answer_piece = _extract_delta_text(delta.get("content"))

            # 有些服务会把最终文本放在 message 而不是 delta
            if not reasoning_piece and not answer_piece:
                message = choice.get("message") or {}
                answer_piece = _extract_delta_text(message.get("content"))

            if reasoning_piece or answer_piece:
                if ttft_any_ms is None:
                    ttft_any_ms = now_ms() - t0

            if reasoning_piece:
                reasoning_parts.append(reasoning_piece)

            if answer_piece:
                answer_parts.append(answer_piece)
                if ttft_answer_ms is None:
                    ttft_answer_ms = now_ms() - t0

    t1 = now_ms()
    e2e_ms = t1 - t0

    if ttft_any_ms is None:
        ttft_any_ms = e2e_ms
    if ttft_answer_ms is None:
        # 没抓到 answer token 时，退化为 ttft_any
        ttft_answer_ms = ttft_any_ms

    return {
        "ttft_any_ms": ttft_any_ms,
        "ttft_answer_ms": ttft_answer_ms,
        "e2e_latency_ms": e2e_ms,
        "reasoning_text": "".join(reasoning_parts),
        "answer_text": "".join(answer_parts),
        "usage": usage_obj,
        "final_obj": final_obj,
    }


def nonstream_chat_completion(api_url: str, payload: Dict[str, Any], timeout: int = 600) -> Tuple[float, Dict[str, Any]]:
    t0 = now_ms()
    data = http_json(api_url, payload, timeout=timeout)
    t1 = now_ms()
    return t1 - t0, data
