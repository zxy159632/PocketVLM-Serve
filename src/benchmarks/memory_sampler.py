from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def read_proc_mem_kb(pid: int) -> Dict[str, Optional[int]]:
    data = {"rss_kb": None, "pss_kb": None}
    status_path = Path(f"/proc/{pid}/status")
    smaps_rollup_path = Path(f"/proc/{pid}/smaps_rollup")

    try:
        txt = status_path.read_text(errors="ignore")
        match = re.search(r"^VmRSS:\s+(\d+)\s+kB", txt, flags=re.M)
        if match:
            data["rss_kb"] = int(match.group(1))
    except Exception:
        pass

    try:
        txt = smaps_rollup_path.read_text(errors="ignore")
        match = re.search(r"^Pss:\s+(\d+)\s+kB", txt, flags=re.M)
        if match:
            data["pss_kb"] = int(match.group(1))
    except Exception:
        pass

    return data


class ProcSampler:
    def __init__(self, pid: Optional[int], interval_s: float = 0.2):
        self.pid = pid
        self.interval_s = interval_s
        self._stop = threading.Event()
        self.samples: List[Dict[str, Any]] = []
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.pid:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            mem = read_proc_mem_kb(self.pid)
            mem["ts"] = time.time()
            self.samples.append(mem)
            time.sleep(self.interval_s)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

    def summary(self) -> Dict[str, Optional[int]]:
        rss_vals = [x["rss_kb"] for x in self.samples if x.get("rss_kb") is not None]
        pss_vals = [x["pss_kb"] for x in self.samples if x.get("pss_kb") is not None]
        return {
            "rss_kb_min": min(rss_vals) if rss_vals else None,
            "rss_kb_max": max(rss_vals) if rss_vals else None,
            "pss_kb_min": min(pss_vals) if pss_vals else None,
            "pss_kb_max": max(pss_vals) if pss_vals else None,
        }
