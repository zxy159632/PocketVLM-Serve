#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 获取当前文件的绝对路径
CURRENT_FILE = Path(__file__).resolve()
# 向上跳两级：src/benchmarks/ -> src/ -> 项目根目录
PROJECT_ROOT = CURRENT_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 现在可以正常导入了
from src.utils.json_io import read_json


def format_stat_block(title: str, stats: dict) -> str:
    return (
        f"{title}: mean={stats.get('mean')} "
        f"p50={stats.get('p50')} p95={stats.get('p95')} "
        f"min={stats.get('min')} max={stats.get('max')}"
    )


def print_summary(report: dict) -> None:
    summary = report.get("summary") or {}
    aggregate = report.get("aggregate") or {}
    process_memory = report.get("process_memory") or {}

    print("===== REPORT =====")
    print(f"mode={report.get('mode')} model={report.get('model')} requests={report.get('requests')} concurrency={report.get('concurrency')}")
    print(format_stat_block("TTFT(ms)", summary.get("ttft_ms") or {}))
    print(format_stat_block("E2E(ms)", summary.get("e2e_latency_ms") or {}))
    print(format_stat_block("Prefill TPS", summary.get("prefill_tps") or {}))
    print(format_stat_block("Decode TPS", summary.get("decode_tps") or {}))
    print(format_stat_block("E2E TPS", summary.get("e2e_tps") or {}))
    print(f"success_rate={summary.get('success_rate')}")
    print(f"wall_time_ms={aggregate.get('wall_time_ms')} rps={aggregate.get('rps')}")
    print(
        f"rss_kb_min={process_memory.get('rss_kb_min')} "
        f"rss_kb_max={process_memory.get('rss_kb_max')} "
        f"pss_kb_min={process_memory.get('pss_kb_min')} "
        f"pss_kb_max={process_memory.get('pss_kb_max')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Print compact summary from benchmark_result.json")
    parser.add_argument("report_json", help="Path to benchmark json report")
    args = parser.parse_args()

    report = read_json(Path(args.report_json))
    print_summary(report)


if __name__ == "__main__":
    main()
