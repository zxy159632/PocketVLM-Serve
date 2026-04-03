from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    prompt: str
    image_path: Optional[str] = None
    max_tokens: int = 128
    temperature: float = 0.2
    stream: bool = True
    description: str = ""


DEFAULT_CASES: Dict[str, BenchmarkCase] = {
    "text_short_64": BenchmarkCase(
        name="text_short_64",
        prompt="请用60字以内介绍Transformer的核心思想。",
        max_tokens=64,
        temperature=0.2,
        stream=True,
        description="短文本、受控输出长度，适合看 TTFT 和 decode 稳定性。",
    ),
    "text_medium_128": BenchmarkCase(
        name="text_medium_128",
        prompt="请简要解释什么是KV Cache，并说明它为什么能提升大模型推理效率。",
        max_tokens=128,
        temperature=0.2,
        stream=True,
        description="中等文本，适合比较热态吞吐和长尾。",
    ),
    "image_short_64": BenchmarkCase(
        name="image_short_64",
        prompt="请用一句话简洁描述图片内容。",
        max_tokens=64,
        temperature=0.2,
        stream=True,
        description="短图像描述，适合比较冷/热首图差异。",
    ),
    "image_medium_128": BenchmarkCase(
        name="image_medium_128",
        prompt="请分3点描述图片主要内容，尽量简洁。",
        max_tokens=128,
        temperature=0.2,
        stream=True,
        description="中等图像描述，适合看图像 prefill 压力。",
    ),
}


def get_case(case_name: Optional[str]) -> Optional[BenchmarkCase]:
    if not case_name:
        return None
    return DEFAULT_CASES.get(case_name)
