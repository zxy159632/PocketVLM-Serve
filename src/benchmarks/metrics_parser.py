from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MetricsInfo:
    raw: Dict[str, float]

    def get(self, key: str) -> Optional[float]:
        return self.raw.get(key)

    def snapshot(self) -> dict:
        return {
            "prompt_tokens_seconds": self.raw.get("llamacpp:prompt_tokens_seconds"),
            "predicted_tokens_seconds": self.raw.get("llamacpp:predicted_tokens_seconds"),
            "kv_cache_usage_ratio": self.raw.get("llamacpp:kv_cache_usage_ratio"),
            "kv_cache_tokens": self.raw.get("llamacpp:kv_cache_tokens"),
            "requests_processing": self.raw.get("llamacpp:requests_processing"),
        }


def fetch_text(url: str, timeout: int = 60) -> str:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_prometheus_text(text: str) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        key = parts[0]
        value = parts[-1]
        try:
            result[key] = float(value)
        except ValueError:
            continue
    return result


def get_metrics(metrics_url: Optional[str], timeout: int = 60) -> Optional[MetricsInfo]:
    if not metrics_url:
        return None
    try:
        text = fetch_text(metrics_url, timeout=timeout)
        return MetricsInfo(raw=parse_prometheus_text(text))
    except Exception:
        return None


def delta_metric(before: Optional[MetricsInfo], after: Optional[MetricsInfo], key: str) -> Optional[float]:
    if not before or not after:
        return None
    before_val = before.get(key)
    after_val = after.get(key)
    if before_val is None or after_val is None:
        return None
    return after_val - before_val
