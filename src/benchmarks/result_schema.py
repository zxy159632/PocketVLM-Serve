from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from src.utils.text_clean import make_preview, strip_empty_think_tags
from src.utils.time_utils import basic_stats


@dataclass
class RequestResult:
    ok: bool = False
    ttft_ms: Optional[float] = None
    e2e_latency_ms: Optional[float] = None
    prompt_tokens: Optional[float] = None
    completion_tokens: Optional[float] = None
    raw_text_preview: Optional[str] = None
    visible_text_preview: Optional[str] = None
    raw_text: Optional[str] = None
    visible_text: Optional[str] = None
    error: Optional[str] = None
    prefill_tps: Optional[float] = None
    decode_tps: Optional[float] = None
    e2e_tps: Optional[float] = None
    server_metrics_after: Optional[Dict[str, Any]] = None
    request_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def finalize_text_fields(result: Dict[str, Any], text: Optional[str]) -> None:
    raw_text = text or ""
    visible_text = strip_empty_think_tags(raw_text)
    result["raw_text"] = raw_text
    result["visible_text"] = visible_text
    result["raw_text_preview"] = make_preview(raw_text, limit=160, remove_think=False)
    result["visible_text_preview"] = make_preview(visible_text, limit=160, remove_think=False)


def enrich_speed_metrics(result: Dict[str, Any]) -> None:
    ttft_ms = result.get("ttft_ms")
    e2e_ms = result.get("e2e_latency_ms")
    prompt_tokens = result.get("prompt_tokens")
    completion_tokens = result.get("completion_tokens")

    if prompt_tokens is not None and ttft_ms not in (None, 0):
        result["prefill_tps"] = float(prompt_tokens) / (float(ttft_ms) / 1000.0)
    else:
        result["prefill_tps"] = None

    decode_ms = None
    if ttft_ms is not None and e2e_ms is not None:
        decode_ms = max(float(e2e_ms) - float(ttft_ms), 0.0)

    if completion_tokens is not None and decode_ms and decode_ms > 0:
        result["decode_tps"] = float(completion_tokens) / (decode_ms / 1000.0)
    else:
        result["decode_tps"] = None

    if completion_tokens is not None and e2e_ms not in (None, 0):
        result["e2e_tps"] = float(completion_tokens) / (float(e2e_ms) / 1000.0)
    else:
        result["e2e_tps"] = None


def summarize_requests(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok_results = [r for r in results if r.get("ok")]
    ttfts = [float(r["ttft_ms"]) for r in ok_results if r.get("ttft_ms") is not None]
    e2es = [float(r["e2e_latency_ms"]) for r in ok_results if r.get("e2e_latency_ms") is not None]
    prefill = [float(r["prefill_tps"]) for r in ok_results if r.get("prefill_tps") is not None]
    decode = [float(r["decode_tps"]) for r in ok_results if r.get("decode_tps") is not None]
    e2e_tps = [float(r["e2e_tps"]) for r in ok_results if r.get("e2e_tps") is not None]
    prompt_tokens = [float(r["prompt_tokens"]) for r in ok_results if r.get("prompt_tokens") is not None]
    completion_tokens = [float(r["completion_tokens"]) for r in ok_results if r.get("completion_tokens") is not None]

    return {
        "requests_total": len(results),
        "requests_ok": len(ok_results),
        "success_rate": (len(ok_results) / len(results)) if results else None,
        "ttft_ms": basic_stats(ttfts),
        "e2e_latency_ms": basic_stats(e2es),
        "prefill_tps": basic_stats(prefill),
        "decode_tps": basic_stats(decode),
        "e2e_tps": basic_stats(e2e_tps),
        "prompt_tokens": basic_stats(prompt_tokens),
        "completion_tokens": basic_stats(completion_tokens),
    }
