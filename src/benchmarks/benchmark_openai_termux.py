#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.benchmarks.benchmark_cases import DEFAULT_CASES, get_case
from src.benchmarks.memory_sampler import ProcSampler
from src.benchmarks.metrics_parser import delta_metric, get_metrics
from src.benchmarks.result_schema import enrich_speed_metrics, finalize_text_fields, summarize_requests
from src.client.openai_client import build_payload, nonstream_chat_completion, stream_chat_completion
from src.utils.json_io import write_json
from src.utils.time_utils import iso_now, now_ms


def read_pid(pid_file: Optional[str]) -> Optional[int]:
    if not pid_file:
        return None
    try:
        return int(Path(pid_file).read_text().strip())
    except Exception:
        return None


def load_prompt_text(prompt: str, prompt_file: Optional[str]) -> str:
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8", errors="ignore")
    return prompt


def one_request(
    api_url: str,
    metrics_url: Optional[str],
    model: str,
    prompt_text: str,
    image_path: Optional[str],
    max_tokens: int,
    temperature: float,
    use_stream: bool,
    timeout: int,
    extra_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = build_payload(
        model=model,
        prompt_text=prompt_text,
        image_path=image_path,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=use_stream,
        extra_body=extra_body,
    )

    before = get_metrics(metrics_url) if metrics_url else None
    result: Dict[str, Any] = {
        "ok": False,
        "ttft_ms": None,              # 保留兼容：默认用“首个 answer token”
        "ttft_any_ms": None,          # 新增：首个任意有效流式块
        "ttft_answer_ms": None,       # 新增：首个真正回答 token
        "e2e_latency_ms": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "raw_text_preview": None,
        "visible_text_preview": None,
        "raw_text": None,
        "visible_text": None,
        "reasoning_text": "",
        "answer_text": "",
        "error": None,
        "prefill_tps": None,
        "decode_tps": None,
        "e2e_tps": None,
        "server_metrics_after": None,
    }

    try:
        if use_stream:
            stream_res = stream_chat_completion(api_url, payload, timeout=timeout)

            result["ttft_any_ms"] = stream_res["ttft_any_ms"]
            result["ttft_answer_ms"] = stream_res["ttft_answer_ms"]
            result["ttft_ms"] = stream_res["ttft_answer_ms"] or stream_res["ttft_any_ms"]
            result["e2e_latency_ms"] = stream_res["e2e_latency_ms"]

            result["reasoning_text"] = stream_res.get("reasoning_text") or ""
            result["answer_text"] = stream_res.get("answer_text") or ""

            # 最终展示文本：优先 answer_text，若空则退化到 reasoning_text
            final_text = result["answer_text"] or result["reasoning_text"]
            finalize_text_fields(result, final_text)

            usage = stream_res.get("usage") or {}
            if isinstance(usage, dict):
                result["prompt_tokens"] = usage.get("prompt_tokens")
                result["completion_tokens"] = usage.get("completion_tokens")

        else:
            e2e_ms, data = nonstream_chat_completion(api_url, payload, timeout=timeout)
            result["e2e_latency_ms"] = e2e_ms
            text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content"))
            finalize_text_fields(result, text)

            usage = data.get("usage") or {}
            if isinstance(usage, dict):
                result["prompt_tokens"] = usage.get("prompt_tokens")
                result["completion_tokens"] = usage.get("completion_tokens")

        result["ok"] = True

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        result["error"] = f"HTTP {exc.code}: {body[:500]}"
    except URLError as exc:
        result["error"] = f"URL error: {exc}"
    except Exception as exc:
        result["error"] = repr(exc)

    after = get_metrics(metrics_url) if metrics_url else None

    # 没拿到 usage 时，再尝试 metrics delta
    if result["prompt_tokens"] is None:
        result["prompt_tokens"] = delta_metric(before, after, "llamacpp:prompt_tokens_total")
    if result["completion_tokens"] is None:
        result["completion_tokens"] = delta_metric(before, after, "llamacpp:tokens_predicted_total")

    enrich_speed_metrics(result)

    # 给热态图像一个标记，避免误解 prompt_tokens=4 就是“整条输入只有 4 token”
    if image_path:
        result["prompt_tokens_note"] = (
            "For multimodal hot-path requests, prompt_tokens may reflect processed/new tokens "
            "after cache reuse, not necessarily the full logical input length."
        )

    if after:
        result["server_metrics_after"] = after.snapshot()

    return result


def run_sequential(
    api_url: str,
    metrics_url: Optional[str],
    model: str,
    prompt_text: str,
    image_path: Optional[str],
    max_tokens: int,
    temperature: float,
    requests_n: int,
    use_stream: bool,
    timeout: int,
    extra_body: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for i in range(requests_n):
        res = one_request(
            api_url=api_url,
            metrics_url=metrics_url,
            model=model,
            prompt_text=prompt_text,
            image_path=image_path,
            max_tokens=max_tokens,
            temperature=temperature,
            use_stream=use_stream,
            timeout=timeout,
            extra_body=extra_body,
        )
        res["request_index"] = i + 1
        results.append(res)
        print(
            f"[{i+1}/{requests_n}] ok={res['ok']} "
            f"ttft_ms={res.get('ttft_ms')} e2e_ms={res.get('e2e_latency_ms')} "
            f"decode_tps={res.get('decode_tps')}"
        )
    return results


def run_concurrent(
    api_url: str,
    metrics_url: Optional[str],
    model: str,
    prompt_text: str,
    image_path: Optional[str],
    max_tokens: int,
    temperature: float,
    requests_n: int,
    concurrency: int,
    use_stream: bool,
    timeout: int,
    extra_body: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], float, Optional[dict], Optional[dict]]:
    before = get_metrics(metrics_url) if metrics_url else None
    t0 = now_ms()
    results: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                one_request,
                api_url,
                None,  # 并发下单请求 metrics delta 不可靠，这里只做 aggregate
                model,
                prompt_text,
                image_path,
                max_tokens,
                temperature,
                use_stream,
                timeout,
                extra_body,
            )
            for _ in range(requests_n)
        ]

        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            res = future.result()
            res["request_index"] = idx
            results.append(res)
            print(
                f"[done {idx}/{requests_n}] ok={res['ok']} "
                f"ttft_ms={res.get('ttft_ms')} e2e_ms={res.get('e2e_latency_ms')}"
            )

    t1 = now_ms()
    after = get_metrics(metrics_url) if metrics_url else None
    return results, (t1 - t0), before.snapshot() if before else None, after.snapshot() if after else None


def build_aggregate_for_concurrent(
    results: List[Dict[str, Any]],
    wall_time_ms: float,
    metrics_before: Optional[dict],
    metrics_after: Optional[dict],
    raw_before_metrics: Optional[Any],
    raw_after_metrics: Optional[Any],
) -> Dict[str, Any]:
    aggregate: Dict[str, Any] = {
        "wall_time_ms": wall_time_ms,
        "rps": (len(results) / (wall_time_ms / 1000.0)) if wall_time_ms > 0 else None,
    }

    if raw_before_metrics and raw_after_metrics:
        prompt_delta = delta_metric(raw_before_metrics, raw_after_metrics, "llamacpp:prompt_tokens_total")
        pred_delta = delta_metric(raw_before_metrics, raw_after_metrics, "llamacpp:tokens_predicted_total")
        aggregate["prompt_tokens_total_delta"] = prompt_delta
        aggregate["completion_tokens_total_delta"] = pred_delta
        if wall_time_ms > 0:
            aggregate["aggregate_prompt_tps"] = (prompt_delta / (wall_time_ms / 1000.0)) if prompt_delta is not None else None
            aggregate["aggregate_decode_tps"] = (pred_delta / (wall_time_ms / 1000.0)) if pred_delta is not None else None
    aggregate["server_metrics_after"] = metrics_after
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OpenAI-compatible llama-server on Termux / Linux.")
    parser.add_argument("--url", default="http://127.0.0.1:8081/v1/chat/completions")
    parser.add_argument("--metrics-url", default="http://127.0.0.1:8081/metrics")
    parser.add_argument("--model", default="qwen35-vlm")
    parser.add_argument("--case", choices=sorted(DEFAULT_CASES.keys()))
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--prompt", default="请用两句话介绍你自己。")
    parser.add_argument("--prompt-file")
    parser.add_argument("--image")
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--pid-file", default=None)
    parser.add_argument("--output-json", default="benchmark_result.json")
    parser.add_argument("--sample-mem-interval", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--stream", dest="stream", action="store_true", help="Use streaming mode.")
    parser.add_argument("--no-stream", dest="stream", action="store_false", help="Use non-stream mode.")
    parser.set_defaults(stream=True)
    args = parser.parse_args()

    if args.list_cases:
        for case in DEFAULT_CASES.values():
            print(f"{case.name}: {case.description}")
        return

    selected_case = get_case(args.case)
    prompt_text = load_prompt_text(args.prompt, args.prompt_file)
    image_path = args.image
    max_tokens = args.max_tokens
    temperature = args.temperature
    use_stream = args.stream

    if selected_case:
        prompt_text = selected_case.prompt
        max_tokens = selected_case.max_tokens
        temperature = selected_case.temperature
        use_stream = selected_case.stream
        if selected_case.image_path and not image_path:
            image_path = selected_case.image_path

    started_at_epoch = time.time()
    started_at_iso = iso_now()

    initial_metrics = get_metrics(args.metrics_url)
    metrics_available = initial_metrics is not None
    metrics_url = args.metrics_url if metrics_available else None

    pid = read_pid(args.pid_file)
    sampler = ProcSampler(pid=pid, interval_s=args.sample_mem_interval)
    sampler.start()

    raw_before_metrics = get_metrics(metrics_url) if metrics_url else None
    aggregate: Dict[str, Any] = {}

    try:
        if args.concurrency <= 1:
            results = run_sequential(
                api_url=args.url,
                metrics_url=metrics_url,
                model=args.model,
                prompt_text=prompt_text,
                image_path=image_path,
                max_tokens=max_tokens,
                temperature=temperature,
                requests_n=args.requests,
                use_stream=use_stream,
                timeout=args.timeout,
            )
            aggregate["wall_time_ms"] = sum(float(r.get("e2e_latency_ms") or 0) for r in results)
        else:
            before_metrics = get_metrics(metrics_url) if metrics_url else None
            results, wall_time_ms, _, _ = run_concurrent(
                api_url=args.url,
                metrics_url=metrics_url,
                model=args.model,
                prompt_text=prompt_text,
                image_path=image_path,
                max_tokens=max_tokens,
                temperature=temperature,
                requests_n=args.requests,
                concurrency=args.concurrency,
                use_stream=use_stream,
                timeout=args.timeout,
            )
            after_metrics = get_metrics(metrics_url) if metrics_url else None
            aggregate = build_aggregate_for_concurrent(
                results=results,
                wall_time_ms=wall_time_ms,
                metrics_before=before_metrics.snapshot() if before_metrics else None,
                metrics_after=after_metrics.snapshot() if after_metrics else None,
                raw_before_metrics=before_metrics,
                raw_after_metrics=after_metrics,
            )
    finally:
        sampler.stop()

    report = {
        "started_at": started_at_epoch,
        "started_at_iso": started_at_iso,
        "mode": "multimodal" if image_path else "text",
        "api_url": args.url,
        "metrics_url": metrics_url,
        "metrics_available": metrics_available,
        "model": args.model,
        "case": args.case,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": use_stream,
        "prompt": prompt_text,
        "image_path": image_path,
        "pid": pid,
        "summary": summarize_requests(results),
        "aggregate": aggregate,
        "process_memory": sampler.summary(),
        "raw_results": results,
    }

    write_json(args.output_json, report)

    print("\n===== SUMMARY =====")
    from pprint import pprint
    pprint(report["summary"])
    if report["aggregate"]:
        print("\n===== AGGREGATE =====")
        pprint(report["aggregate"])
    if report["process_memory"]:
        print("\n===== PROCESS MEMORY =====")
        pprint(report["process_memory"])
    print(f"\nSaved report to: {Path(args.output_json).resolve()}")


if __name__ == "__main__":
    main()
