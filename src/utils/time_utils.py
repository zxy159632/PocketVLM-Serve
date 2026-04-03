from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import Iterable, List, Optional


def now_ms() -> float:
    """High precision monotonic time in milliseconds."""
    return time.perf_counter() * 1000.0


def percentile(values: Iterable[float], p: float) -> Optional[float]:
    vals = sorted(float(v) for v in values)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    d0 = vals[f] * (c - k)
    d1 = vals[c] * (k - f)
    return d0 + d1


def basic_stats(values: Iterable[float]) -> dict:
    vals: List[float] = [float(v) for v in values]
    if not vals:
        return {"mean": None, "p50": None, "p95": None, "min": None, "max": None}
    return {
        "mean": statistics.mean(vals),
        "p50": percentile(vals, 50),
        "p95": percentile(vals, 95),
        "min": min(vals),
        "max": max(vals),
    }


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()
