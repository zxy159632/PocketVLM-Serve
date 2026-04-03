# Android On-Device Multimodal Model Deployment and Performance Benchmarking: Qwen3.5-0.8B + llama.cpp + Termux

[English](./README_EN.md) | [简体中文](./README.md)

> A real-world engineering project aimed at **LLM deployment / inference acceleration**.
> The goal is not merely to “get the model running,” but to complete the full loop of **model selection, on-device deployment, service packaging, benchmarking, parameter tuning, and issue diagnosis**, and then document it as a reproducible project record.

---

## 1. Project Goals

This project focuses on two core objectives:

1. **Deploy a multimodal model locally on an Android phone and expose it as a service**;
2. **Run performance benchmarking and parameter tuning on a real device**, producing interpretable conclusions instead of only showing that the model can run.

Final deliverables:

- Run `llama.cpp/llama-server` locally on the phone
- Provide an OpenAI-compatible HTTP API
- Support both text and image requests
- Provide a web demo and Python test scripts
- Provide a reusable benchmark pipeline
- Output structured benchmark results (JSON + summary)

---

## 2. Project Background and Technical Choices

The project is centered on the skill set required for **LLM deployment / inference acceleration internships**. Therefore, the emphasis is not on building a complex frontend, but on demonstrating the following capabilities:

- Inference framework selection
- On-device model format adaptation
- Service packaging
- Benchmark script development
- Metric collection and result analysis
- Performance tuning and issue diagnosis on real hardware

The key technical decisions are as follows.

### 2.1 Why `llama.cpp` was chosen for the phone side

The target requirements on mobile are:

- Local offline inference
- Operation in a resource-constrained environment
- A unified HTTP interface for external access

The final stack is therefore:

- `llama.cpp`: lightweight, buildable, and suitable for CPU-first edge deployment
- `GGUF`: model format well suited for llama.cpp
- `Termux`: turns an Android phone into a manageable Linux-like environment
- `llama-server`: directly exposes an OpenAI-compatible API

### 2.2 Why the final version is CPU-first

A full Vulkan / GPU path was attempted during the project, but on the Android device it ran into shader / compute pipeline creation failures, which eventually manifested as low-level crashes or segmentation faults. After investigation, this was not a simple command issue, but more likely related to:

- Android GPU driver compatibility
- The maturity of Vulkan shader support
- The practical viability of K-series quantization on mobile GPUs

Therefore, **all stable demos and benchmark results in the current version are based on CPU inference**. This is a typical engineering tradeoff: prioritize reproducibility, interpretability, and stability.

---

## 3. Hardware and Software Environment

### 3.1 Device environment

- Phone: **Redmi K90 (12 GB + 256 GB)**
- System environment: Android + Termux
- Inference mode: **CPU inference**

### 3.2 Model and runtime

- Main model: `Qwen3.5-0.8B-Q4_K_M.gguf`
- Multimodal projection: `mmproj-F16.gguf`
- Inference engine: `llama.cpp`
- Service component: `llama-server`
- API protocol: OpenAI-compatible API

### 3.3 Service endpoint

```text
http://127.0.0.1:8081/v1/chat/completions
```

The model is served under the alias:

```text
qwen35-vlm
```

---

## 4. Current Project Structure

The repository has evolved from a pure deployment demo into a more complete engineering project covering **deployment + benchmarking + result documentation**:

```text
mobile_llm/
├── llama.cpp/
├── logs/
├── models/
├── pids/
├── results/
│   ├── baseline_*.json
│   ├── benchmark_runs/
│   │   ├── threads_sweep_20260401_144940/
│   │   ├── threads_sweep_20260401_215335/
│   │   └── warmup/
├── scripts/
│   ├── boot_demo.sh
│   ├── start_qwen_server.sh
│   ├── start_bench.sh
│   ├── sweep_threads.sh
│   ├── warmup.sh
│   ├── warmup_image.sh
│   ├── start_web.sh
│   ├── stop_demo.sh
│   ├── test_image.py
│   ├── watch_llama_log.sh
│   └── watch_web_log.sh
├── src/
│   ├── benchmarks/
│   │   ├── benchmark_cases.py
│   │   ├── benchmark_openai_termux.py
│   │   ├── memory_sampler.py
│   │   ├── metrics_parser.py
│   │   ├── report_summary.py
│   │   └── result_schema.py
│   ├── client/
│   │   └── openai_client.py
│   └── utils/
│       ├── image_utils.py
│       ├── json_io.py
│       ├── text_clean.py
│       └── time_utils.py
├── web_demo/
│   └── index.html
└── README.md
```

Compared with the pre-benchmark version, the important additions are no longer just startup scripts, but also:

- benchmark case definitions
- the main OpenAI-compatible benchmark runner
- `/metrics` parsing and token statistics
- process RSS / PSS sampling
- parameter sweep scripts
- result JSON files and summary output

---

## 5. Mobile Deployment Pipeline

### 5.1 Base environment setup

```bash
pkg update
pkg upgrade
termux-wake-lock
pkg install -y git cmake clang make python wget curl ninja
```

To access photos from the phone gallery:

```bash
termux-setup-storage
```

### 5.2 Directory setup

```bash
mkdir -p ~/zxy/mobile_llm/models
mkdir -p ~/zxy/mobile_llm/scripts
mkdir -p ~/zxy/mobile_llm/venvs
```

### 5.3 Python environment

The project uses `venv` for Python dependencies needed for model download and benchmarking, to avoid introducing an overly heavy environment on the phone:

```bash
python -m venv ~/zxy/mobile_llm/venvs/modelscope_env
source ~/zxy/mobile_llm/venvs/modelscope_env/bin/activate
pip install -U pip setuptools wheel
pip install -U modelscope
```

### 5.4 Download models

```bash
modelscope download --model unsloth/Qwen3.5-0.8B-GGUF \
  --include "Qwen3.5-0.8B-Q4_K_M.gguf" \
  --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M

modelscope download --model unsloth/Qwen3.5-0.8B-GGUF \
  --include "mmproj-F16.gguf" \
  --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M
```

### 5.5 Build `llama.cpp`

```bash
cd ~/zxy/mobile_llm
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j 4
```

After the build, you should at least see:

- `llama-cli`
- `llama-server`

### 5.6 Minimal CLI verification

```bash
MODEL_DIR="$HOME/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M"
MODEL_FILE=$(find "$MODEL_DIR" -maxdepth 1 -name "*.gguf" ! -name "mmproj*" | head -n 1)

./build/bin/llama-cli \
  -m "$MODEL_FILE" \
  -p "Please explain Transformer in three sentences."
```

Once CLI inference works, the next step is service packaging.

---

## 6. Service Packaging

### 6.1 Production service startup

The project uses the following script in practice:

```bash
bash scripts/start_qwen_server.sh
```

Core startup parameters:

- `--mmproj`: enables the image path
- `-c 8192`: sets the context window to 8192
- `--reasoning off`: disables reasoning to avoid long `<think>` output occupancy
- `--metrics`: enables `/metrics` for later benchmark collection
- `--alias qwen35-vlm`: defines a unified model name

Corresponding service endpoints:

```text
http://127.0.0.1:8081/v1/chat/completions
http://127.0.0.1:8081/metrics
```

### 6.2 Web demo

Start the static webpage:

```bash
bash scripts/start_web.sh
```

Access it at:

```text
http://127.0.0.1:8090/index.html
```

### 6.3 One-click demo script

The project provides:

```bash
bash scripts/boot_demo.sh
```

This script performs the following steps:

1. Start `llama-server`
2. Poll until the service is ready
3. Run text warmup
4. Start the local web server

To stop all services:

```bash
bash scripts/stop_demo.sh
```

---

## 7. Benchmark System Design

This is the most important addition in the post-benchmark version.

### 7.1 Benchmark goals

Performance testing is not only about asking whether the system is “fast,” but about decomposing performance into the following dimensions:

- **TTFT**: time to first token
- **E2E latency**: end-to-end response time
- **Prefill TPS**: throughput during the prefill stage
- **Decode TPS**: throughput during the decode stage
- **E2E TPS**: overall end-to-end throughput
- **RSS / PSS**: process memory usage range
- **Success rate**: whether requests complete stably

### 7.2 Benchmark code structure

- `src/benchmarks/benchmark_cases.py`: unified case definitions
- `src/benchmarks/benchmark_openai_termux.py`: main benchmark runner
- `src/benchmarks/metrics_parser.py`: parses `/metrics`
- `src/benchmarks/memory_sampler.py`: samples process memory
- `src/benchmarks/result_schema.py`: organizes result structures and summaries
- `src/benchmarks/report_summary.py`: outputs compact summaries

### 7.3 Predefined benchmark cases

The current version includes three core cases:

- `text_short_64`: short text, output cap 64
- `text_medium_128`: medium text, output cap 128
- `image_short_64`: short image description, output cap 64

### 7.4 Unified benchmark entry point

Start the benchmark service with metrics enabled:

```bash
bash scripts/start_bench.sh
```

Run a single case:

```bash
python src/benchmarks/benchmark_openai_termux.py \
  --url http://127.0.0.1:8081/v1/chat/completions \
  --metrics-url http://127.0.0.1:8081/metrics \
  --model qwen35-vlm \
  --case text_short_64 \
  --requests 10 \
  --pid-file ~/zxy/mobile_llm/pids/llama_server.pid \
  --output-json results/sample_text_short.json
```

Run batch sweeps:

```bash
bash scripts/sweep_threads.sh
```

The current sweep script supports two experiment families:

1. `-t / -tb` sweep: tests the impact of `THREADS` and `THREADS_BATCH`
2. `-ub` sweep: tests the impact of `UBATCH`

---

## 8. Benchmark Configuration

The repository already contains two rounds of formal sweep results, both from **2026-04-01**.

### 8.1 Shared environment parameters

Most sweeps use the following core configuration:

- `CTX_SIZE=8192`
- `PARALLEL=2`
- `BATCH_SIZE=512`
- `CONCURRENCY_TEXT=1`
- `CONCURRENCY_IMAGE=1`
- `TEXT_REQUESTS=10`
- `IMAGE_REQUESTS=5`
- Model alias: `qwen35-vlm`
- Image sample: `~/storage/dcim/Camera/test.jpg`

### 8.2 Thread sweep

Fixed:

- `UBATCH=256`

Combinations:

- `t=2, tb=4`
- `t=4, tb=4`
- `t=4, tb=6`
- `t=6, tb=6`

### 8.3 UBATCH sweep

Fixed:

- `t=4, tb=4`

Combinations:

- `ub=128`
- `ub=256`
- `ub=512`

---

## 9. Baseline Benchmark Results

### 9.1 Text baselines

| Scenario | Requests | Concurrency | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---|---:|---:|---:|---:|---:|---:|
| `text_short_64` sequential | 10 | 1 | 144.0 ms | 920.4 ms | 57.7 tok/s | 0.80 GiB |
| `text_medium_128` sequential | 10 | 1 | 181.4 ms | 2521.9 ms | 55.0 tok/s | 1.04 GiB |
| `text_medium_128` concurrent | 20 | 2 | 356.6 ms | 5216.9 ms | 27.2 tok/s (per request) | 1.69 GiB |

Additional notes:

- Aggregate decode throughput for `text_medium_128` at concurrency 2 is about **49.1 tok/s**.
- Text cases are already fairly stable overall, with a **100% success rate**.

### 9.2 Image baselines

| Scenario | Requests | Concurrency | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---|---:|---:|---:|---:|---:|---:|
| `image_short_64` cold start | 1 | 1 | 198925.5 ms | 199582.3 ms | 42.6 tok/s | 1.54 GiB |
| `image_short_64` warm state | 5 | 1 | 239.8 ms | 1140.5 ms | 38.9 tok/s | 1.52 GiB |

Core findings:

- The **first cold image request is extremely slow**, with TTFT around **198.9 seconds**;
- Once the vision path becomes warm, image TTFT returns to **around 240 ms**;
- Therefore, the core issue on the image side is not steady-state speed, but the **severe long tail on the first image request**.

---

## 10. Sweep Results

### 10.1 `-t / -tb` sweep (fixed `ub=256`)

#### Text results

| `-t` | `-tb` | case | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 4 | `text_short_64` | 188.2 ms | 1363.0 ms | 38.2 tok/s | 2.05 GiB |
| 4 | 4 | `text_short_64` | 151.4 ms | **842.5 ms** | **57.5 tok/s** | 2.11 GiB |
| 4 | 6 | `text_short_64` | **131.5 ms** | 1179.1 ms | 48.0 tok/s | 2.11 GiB |
| 6 | 6 | `text_short_64` | 140.1 ms | 1013.2 ms | 50.2 tok/s | 2.11 GiB |
| 2 | 4 | `text_medium_128` | 186.4 ms | 3604.4 ms | 38.0 tok/s | 2.18 GiB |
| 4 | 4 | `text_medium_128` | 197.7 ms | **2861.0 ms** | 49.3 tok/s | 2.26 GiB |
| 4 | 6 | `text_medium_128` | **165.8 ms** | 2981.2 ms | 47.0 tok/s | 2.31 GiB |
| 6 | 6 | `text_medium_128` | 179.7 ms | 2893.4 ms | **49.4 tok/s** | 2.31 GiB |

#### Image results

| `-t` | `-tb` | case | TTFT mean | TTFT p50 | TTFT p95 | E2E mean |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 4 | `image_short_64` | 56972.6 ms | **238.1 ms** | 227220.0 ms | 58688.1 ms |
| 4 | 4 | `image_short_64` | 34993.5 ms | 268.7 ms | 139188.3 ms | 36099.7 ms |
| 4 | 6 | `image_short_64` | 37750.9 ms | 270.8 ms | 150189.3 ms | 39190.9 ms |
| 6 | 6 | `image_short_64` | **25749.5 ms** | 347.1 ms | **102016.2 ms** | **27177.7 ms** |

#### Conclusions from thread sweep

- For **short text outputs**, `t=4, tb=4` gives the best end-to-end latency, while `t=4, tb=6` gives the lowest TTFT.
- For **medium text outputs**, `t=4, tb=6` reduces TTFT further, while `t=4, tb=4` and `t=6, tb=6` are more balanced in E2E latency and decode throughput.
- For **image requests**, different thread settings can partially affect averages, but **cannot fundamentally eliminate the long tail on the first formal image request**.

---

### 10.2 `-ub` sweep (fixed `t=4, tb=4`)

#### Text results

| `-ub` | case | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---:|---|---:|---:|---:|---:|
| 128 | `text_short_64` | 203.8 ms | 1152.8 ms | 45.6 tok/s | 1.17 GiB |
| 256 | `text_short_64` | **146.1 ms** | 993.6 ms | 55.0 tok/s | 2.11 GiB |
| 512 | `text_short_64` | 155.7 ms | **943.1 ms** | **55.0 tok/s** | 1.30 GiB |
| 128 | `text_medium_128` | 230.4 ms | 3146.8 ms | 44.1 tok/s | 1.18 GiB |
| 256 | `text_medium_128` | 210.8 ms | 2595.9 ms | 54.0 tok/s | 2.24 GiB |
| 512 | `text_medium_128` | **192.8 ms** | **2528.6 ms** | **55.1 tok/s** | 1.42 GiB |

#### Image results

| `-ub` | case | TTFT mean | TTFT p50 | TTFT p95 | E2E mean |
|---:|---|---:|---:|---:|---:|
| 128 | `image_short_64` | 38172.3 ms | 250.7 ms | 151949.7 ms | 39374.0 ms |
| 256 | `image_short_64` | 33050.5 ms | 257.6 ms | 131441.4 ms | 34323.0 ms |
| 512 | `image_short_64` | **29687.8 ms** | 253.5 ms | **117978.4 ms** | **30773.4 ms** |

#### Conclusions from UBATCH sweep

- Under the current device-and-model combination, **`ub=512` is the most favorable for medium text outputs**;
- Both `ub=256` and `ub=512` clearly outperform `ub=128`;
- `ub=512` also improves image **mean / p95**, but **the image long tail still remains**;
- Therefore, in the current version, `ub=512` is the more promising direction to keep.

---

## 11. Final Performance Conclusions

### 11.1 Conclusions on the text side

The current version already supports fairly clear recommendations for text workloads.

#### If lower E2E latency is the priority

Recommended:

```text
-t 4 -tb 4 -ub 512
```

Why:

- `text_short_64` E2E is reduced to **943.1 ms**;
- `text_medium_128` E2E is reduced to **2528.6 ms**;
- Decode throughput remains at about **55 tok/s**;
- It is more stable than `ub=128` and stronger than most other combinations.

#### If lower TTFT is the priority

A possible choice is:

```text
-t 4 -tb 6 -ub 256
```

Why:

- `text_short_64` has the lowest TTFT at **131.5 ms**;
- `text_medium_128` has the lowest TTFT at **165.8 ms**.

However, this combination is not the best overall in E2E latency, so it is more suitable for scenarios where time-to-first-token matters more.

### 11.2 Conclusions on the image side

The image-side conclusion is even more important and more valuable from an engineering perspective:

1. **The vision path steady-state is not bad**; warm-state p50 TTFT is roughly **238–347 ms**;
2. **The real issue is the extreme long tail on the first formal image request**;
3. Even after running `image warmup`, formal tests still show occasional **102–164 second** outlier requests;
4. This indicates that the current warmup strategy **does not fully reuse the critical path of real image requests**, or that there is some additional vision-path initialization / cache invalidation happening later.

In other words:

- Text performance has already moved into the stage of parameter tuning;
- Image performance still has a separate must-fix problem: the **first-image long tail**.

---

## 12. Current Understanding of the Image Long-Tail Issue

Based on the warmup behavior and the formal benchmark results in the repository, the following assessment can be made.

### Confirmed facts

- Cold-start first image request: about **198.9 seconds**;
- After warmup, steady-state image requests can return to roughly **250 ms TTFT**;
- But in sweeps, the **first formal image request** still often shows **100+ second** long tails.

### Current plausible hypotheses

This looks more like one of the following issues rather than a simple thread-parameter problem:

- The warmup request and the formal image case may look similar on the surface, but the **internal service path is not fully reused**;
- The first formal request triggers additional vision-related initialization;
- There is cache invalidation, context reconstruction, or resource cleanup between warmup and the formal case;
- The initialization benefit from the image path is not retained reliably for subsequent formal requests.

### Current-stage conclusion

**The long tail on the first formal image request still requires separate optimization.**

The current README does not present this as “solved.” Instead, it records it as:

- a reproduced phenomenon,
- verified by benchmark runs,
- confirmed to be something that ordinary text-side parameter sweeps cannot solve,
- a problem that should be further investigated through vision warmup paths and service-side reuse behavior.

---

## 13. Key Engineering Issues and How They Were Handled

### 13.1 Vulkan / GPU path failed during build and runtime

Observed symptoms included:

- Vulkan-related build compatibility issues
- compute pipeline creation failures
- shader / driver errors
- segmentation faults on exit

Conclusion:

- This was not a “wrong command” level issue;
- It was more likely related to Android GPU drivers, Vulkan support, and compatibility with quantized shaders;
- Therefore, the CPU path is used as the formal delivery version of the project.

### 13.2 Image requests exceeded the context limit

After image base64 content was inserted into the request body, the effective prompt token count increased significantly. The project encountered errors such as:

```text
request exceeds the available context size (2048 tokens)
```

Solution:

- Increase the context window from `2048` to `8192`
- Use `-c 8192` consistently in both the benchmark service and the production service

### 13.3 The model got stuck in `<think>` without giving a final answer

Observed behavior:

- The request returned normally
- But the model kept outputting reasoning content
- The final `content` was empty or truncated by `max_tokens`

Solution:

```bash
--reasoning off
--reasoning-format none
```

This is necessary for stable interaction in the current mobile setup.

### 13.4 GGUF file path / format issues

The project also encountered errors such as:

```text
failed to read magic
```

This ultimately indicated one of the following:

- The path pointed to a directory or the wrong file
- The downloaded artifact was incomplete
- The file itself was not a valid GGUF

This kind of diagnosis matters just as much as parameter tuning, because deployment engineering is not only about “turning knobs.”

---

## 14. How to Reproduce the Experiments

### 14.1 Start the service

```bash
bash scripts/start_qwen_server.sh
```

### 14.2 Run text warmup

```bash
bash scripts/warmup.sh
```

### 14.3 Run image warmup

```bash
bash scripts/warmup_image.sh
```

### 14.4 Run the sweep

```bash
bash scripts/sweep_threads.sh
```

### 14.5 View a summary

```bash
python src/benchmarks/report_summary.py \
  results/benchmark_runs/threads_sweep_20260401_215335/t4_tb4_ub512/text_medium_128.json
```

### 14.6 View logs

```bash
bash scripts/watch_llama_log.sh
bash scripts/watch_web_log.sh
```

---

## 15. Project Value Summary

The value of this project is not simply that “a model runs on a phone,” but that it covers the following capability chain end to end:

- From understanding server-side inference frameworks to practicing edge deployment
- From model format selection to real GGUF + llama.cpp deployment
- From one-off request validation to OpenAI-compatible service packaging
- From manual experience to automated benchmarking
- From “it runs” to “it can be measured, compared, and explained”
- From deployment success to a clear statement of bottlenecks and unsolved problems

For the direction of LLM deployment / inference acceleration, this carries much more engineering value than a simple “webpage chat demo.”

---

## 16. Next Optimization Directions

The current version has already completed the first-stage closed loop of **deployment + service packaging + benchmarking + parameter tuning**. There are still three clear follow-up optimization tracks.

### 16.1 Optimize the long tail on the first formal image request

This is the top priority. Investigation should focus on:

- Whether warmup content is exactly identical to the formal image case
- Whether the service truly reuses the same path after warmup
- Whether multiple consecutive image warmups are needed
- Whether the vision cache is not being retained stably

### 16.2 Further refine text-side parameters

Future work can continue to explore:

- Different `PARALLEL` settings
- Different `BATCH_SIZE` values
- Aggregate throughput comparisons under text concurrency
- Decode stability under longer output lengths

### 16.3 Visualization and reporting

Results are already saved in structured JSON form. Future improvements can include:

- Automatic Markdown report generation
- TTFT / E2E / TPS curves
- A consolidated summary table across parameter combinations

---

## 17. Summary

This project starts from **local multimodal model deployment on an Android phone**, and expands further into a complete engineering workflow covering **OpenAI-compatible service packaging, automated benchmarking, parameter sweeps, performance analysis, and issue diagnosis**.

The conclusions in the current version are clear:

- **The text pipeline is largely in place and already yields reusable parameter-tuning conclusions**;
- **The image pipeline is usable in the warm state, but the long tail on the first formal request remains the core optimization target for the next stage**.
