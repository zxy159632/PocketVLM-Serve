# PocketVLM-Serve
PocketVLM-Serve: On-Device Multimodal Model Deployment and Benchmarking on Android

> 一个面向**大模型部署 / 推理加速方向**的真实工程项目记录。  
> 目标不是“把模型跑起来就算完成”，而是把**模型选型、端侧部署、服务化封装、基准测试、参数调优、问题定位**完整走通，并沉淀成可复现的项目资料。

---

## 1. 项目目标

本项目聚焦两件事：

1. **在安卓手机本地部署多模态模型，并以服务形式对外提供调用**；
2. **围绕真实设备进行性能测试与参数调优**，形成可解释的性能结论，而不是只展示“能跑”。

最终交付形态：

- 手机本地运行 `llama.cpp/llama-server`
- 提供 OpenAI-compatible HTTP 接口
- 支持文本请求与图像请求
- 提供网页 Demo 与 Python 测试脚本
- 提供一套可复用的 benchmark 脚本链路
- 输出结构化测试结果（JSON + summary）

---

## 2. 项目背景与技术取舍

项目重心是**大模型部署 / 推理加速方向实习**。因此本项目的重点不是做复杂前端，而是展示以下能力：

- 推理框架选型
- 端侧模型格式适配
- 服务化封装
- 测试脚本编写
- 指标采集与结果分析
- 真实设备上的性能调优与问题定位

项目中的核心取舍如下：

### 2.1 为什么手机端选择 llama.cpp

手机端目标是：

- 本地离线推理
- 资源受限环境运行
- 通过 HTTP 接口提供统一调用入口

因此最终采用：

- `llama.cpp`：轻量、可编译、适合端侧 CPU 路线
- `GGUF`：适合 llama.cpp 的模型格式
- `Termux`：将安卓手机转成可操作的 Linux 风格环境
- `llama-server`：直接暴露 OpenAI-compatible 接口

### 2.2 为什么最终以 CPU 路线为主

项目中完整尝试过 Vulkan / GPU 路线，但在安卓设备上遇到 shader / compute pipeline 创建失败，最终表现为底层崩溃或段错误。经过排查，这不是命令写错，而更偏向：

- 安卓 GPU 驱动兼容性
- Vulkan shader 支持成熟度
- K 系列量化在移动端 GPU 上的实际可用性

因此当前版本的**稳定演示与性能测试全部基于 CPU 路线**。这也是一个典型的工程取舍：优先可复现、可解释、可稳定运行。

---

## 3. 硬件与软件环境

### 3.1 设备环境

- 手机：**Redmi K90（12GB + 256GB）**
- 系统环境：Android + Termux
- 推理方式：**CPU 推理**

### 3.2 模型与运行时

- 主模型：`Qwen3.5-0.8B-Q4_K_M.gguf`
- 多模态投影：`mmproj-F16.gguf`
- 推理引擎：`llama.cpp`
- 服务组件：`llama-server`
- 接口协议：OpenAI-compatible API

### 3.3 服务地址

```text
http://127.0.0.1:8081/v1/chat/completions
```

模型服务启动时使用别名：

```text
qwen35-vlm
```

---

## 4. 当前项目结构

当前仓库已经从“单纯部署演示”扩展为“部署 + 测试 + 结果沉淀”的完整工程结构：

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

与测试前版本相比，新增的重点不再只是启动脚本，而是：

- benchmark case 定义
- OpenAI-compatible benchmark 主程序
- `/metrics` 解析与 token 统计
- 进程 RSS / PSS 采样
- 参数 sweep 脚本
- 结果 JSON 与 summary 输出

---

## 5. 手机端部署链路

## 5.1 基础环境准备

```bash
pkg update
pkg upgrade
termux-wake-lock
pkg install -y git cmake clang make python wget curl ninja
```

如需访问手机相册图片：

```bash
termux-setup-storage
```

### 5.2 目录准备

```bash
mkdir -p ~/zxy/mobile_llm/models
mkdir -p ~/zxy/mobile_llm/scripts
mkdir -p ~/zxy/mobile_llm/venvs
```

### 5.3 Python 环境

项目中用于模型下载与 benchmark 的 Python 依赖采用 `venv`，避免在手机端引入过重的环境管理：

```bash
python -m venv ~/zxy/mobile_llm/venvs/modelscope_env
source ~/zxy/mobile_llm/venvs/modelscope_env/bin/activate
pip install -U pip setuptools wheel
pip install -U modelscope
```

### 5.4 下载模型

```bash
modelscope download --model unsloth/Qwen3.5-0.8B-GGUF \
  --include "Qwen3.5-0.8B-Q4_K_M.gguf" \
  --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M

modelscope download --model unsloth/Qwen3.5-0.8B-GGUF \
  --include "mmproj-F16.gguf" \
  --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M
```

### 5.5 编译 llama.cpp

```bash
cd ~/zxy/mobile_llm
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j 4
```

编译完成后至少应看到：

- `llama-cli`
- `llama-server`

### 5.6 CLI 最小验证

```bash
MODEL_DIR="$HOME/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M"
MODEL_FILE=$(find "$MODEL_DIR" -maxdepth 1 -name "*.gguf" ! -name "mmproj*" | head -n 1)

./build/bin/llama-cli \
  -m "$MODEL_FILE" \
  -p "请用三句话介绍一下 Transformer。"
```

CLI 跑通后，再进入服务化阶段。

---

## 6. 服务化封装

### 6.1 正式服务启动

项目中实际使用的启动脚本为：

```bash
bash scripts/start_qwen_server.sh
```

核心启动参数：

- `--mmproj`：启用图像路径
- `-c 8192`：上下文窗口设置为 8192
- `--reasoning off`：关闭 reasoning，避免 `<think>` 长时间占用输出
- `--metrics`：开启 `/metrics`，便于后续 benchmark 采集
- `--alias qwen35-vlm`：设置统一模型名

对应服务接口：

```text
http://127.0.0.1:8081/v1/chat/completions
http://127.0.0.1:8081/metrics
```

### 6.2 Web Demo

启动静态网页：

```bash
bash scripts/start_web.sh
```

访问地址：

```text
http://127.0.0.1:8090/index.html
```

### 6.3 一键演示脚本

项目中提供：

```bash
bash scripts/boot_demo.sh
```

该脚本会完成：

1. 启动 `llama-server`
2. 轮询等待服务就绪
3. 执行文本 warmup
4. 启动本地网页服务

停止服务：

```bash
bash scripts/stop_demo.sh
```

---

## 7. Benchmark 体系设计

这部分是测试后版本最核心的新增内容。

### 7.1 Benchmark 目标

性能测试不是只看“快不快”，而是分解为以下几个维度：

- **TTFT**：首 token 时间
- **E2E latency**：完整响应时间
- **Prefill TPS**：prefill 阶段吞吐
- **Decode TPS**：decode 阶段吞吐
- **E2E TPS**：整体端到端吞吐
- **RSS / PSS**：进程内存占用区间
- **成功率**：请求是否稳定完成

### 7.2 Benchmark 代码结构

- `src/benchmarks/benchmark_cases.py`：统一定义测试 case
- `src/benchmarks/benchmark_openai_termux.py`：主 benchmark 程序
- `src/benchmarks/metrics_parser.py`：解析 `/metrics`
- `src/benchmarks/memory_sampler.py`：采样进程内存
- `src/benchmarks/result_schema.py`：统一整理结果结构与 summary
- `src/benchmarks/report_summary.py`：输出简版 summary

### 7.3 预置测试 case

当前版本包含 3 个核心 case：

- `text_short_64`：短文本、输出上限 64
- `text_medium_128`：中等文本、输出上限 128
- `image_short_64`：短图像描述、输出上限 64

### 7.4 统一 benchmark 启动方式

启动带 metrics 的 benchmark 服务：

```bash
bash scripts/start_bench.sh
```

单 case 测试：

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

批量 sweep：

```bash
bash scripts/sweep_threads.sh
```

当前 sweep 脚本支持两类实验：

1. `-t / -tb` sweep：测试 `THREADS` 与 `THREADS_BATCH` 的影响
2. `-ub` sweep：测试 `UBATCH` 的影响

---

## 8. 测试配置

本仓库内已经保留了两轮正式 sweep 结果，时间均为 **2026-04-01**。

### 8.1 统一环境参数

大部分 sweep 共享以下核心配置：

- `CTX_SIZE=8192`
- `PARALLEL=2`
- `BATCH_SIZE=512`
- `CONCURRENCY_TEXT=1`
- `CONCURRENCY_IMAGE=1`
- `TEXT_REQUESTS=10`
- `IMAGE_REQUESTS=5`
- 模型别名：`qwen35-vlm`
- 图像样本：`~/storage/dcim/Camera/test.jpg`

### 8.2 线程 sweep

固定：

- `UBATCH=256`

组合：

- `t=2, tb=4`
- `t=4, tb=4`
- `t=4, tb=6`
- `t=6, tb=6`

### 8.3 UBATCH sweep

固定：

- `t=4, tb=4`

组合：

- `ub=128`
- `ub=256`
- `ub=512`

---

## 9. 基线测试结果

### 9.1 文本基线

| 场景 | 请求数 | 并发 | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---|---:|---:|---:|---:|---:|---:|
| `text_short_64` 顺序 | 10 | 1 | 144.0 ms | 920.4 ms | 57.7 tok/s | 0.80 GiB |
| `text_medium_128` 顺序 | 10 | 1 | 181.4 ms | 2521.9 ms | 55.0 tok/s | 1.04 GiB |
| `text_medium_128` 并发 | 20 | 2 | 356.6 ms | 5216.9 ms | 27.2 tok/s（单请求） | 1.69 GiB |

补充说明：

- `text_medium_128` 并发 2 的 aggregate decode 吞吐约为 **49.1 tok/s**。
- 文本场景整体已经具备较好的稳定性，成功率均为 **100%**。

### 9.2 图像基线

| 场景 | 请求数 | 并发 | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---|---:|---:|---:|---:|---:|---:|
| `image_short_64` 冷启动 | 1 | 1 | 198925.5 ms | 199582.3 ms | 42.6 tok/s | 1.54 GiB |
| `image_short_64` 热态 | 5 | 1 | 239.8 ms | 1140.5 ms | 38.9 tok/s | 1.52 GiB |

核心结论：

- **首个图像请求冷启动极慢**，TTFT 约 **198.9 秒**；
- 一旦视觉路径进入热态，图像 TTFT 可以回到 **约 240 ms**；
- 因此图像路径的核心问题不是 steady-state 太慢，而是**首图长尾极其严重**。

---

## 10. 参数 sweep 结果

## 10.1 `-t / -tb` sweep（固定 `ub=256`）

### 文本结果

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

### 图像结果

| `-t` | `-tb` | case | TTFT mean | TTFT p50 | TTFT p95 | E2E mean |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 4 | `image_short_64` | 56972.6 ms | **238.1 ms** | 227220.0 ms | 58688.1 ms |
| 4 | 4 | `image_short_64` | 34993.5 ms | 268.7 ms | 139188.3 ms | 36099.7 ms |
| 4 | 6 | `image_short_64` | 37750.9 ms | 270.8 ms | 150189.3 ms | 39190.9 ms |
| 6 | 6 | `image_short_64` | **25749.5 ms** | 347.1 ms | **102016.2 ms** | **27177.7 ms** |

### 线程 sweep 结论

- 对于**文本短输出**，`t=4, tb=4` 的端到端时延最好；`t=4, tb=6` 的 TTFT 最低。
- 对于**文本中等输出**，`t=4, tb=6` 可以进一步压低 TTFT，但 `t=4, tb=4` / `t=6, tb=6` 在整体 E2E 和 decode 吞吐上更均衡。
- 对于**图像请求**，不同线程配置只能部分影响平均值，**无法根治首个正式图像请求长尾**。

---

## 10.2 `-ub` sweep（固定 `t=4, tb=4`）

### 文本结果

| `-ub` | case | TTFT mean | E2E mean | Decode TPS mean | PSS max |
|---:|---|---:|---:|---:|---:|
| 128 | `text_short_64` | 203.8 ms | 1152.8 ms | 45.6 tok/s | 1.17 GiB |
| 256 | `text_short_64` | **146.1 ms** | 993.6 ms | 55.0 tok/s | 2.11 GiB |
| 512 | `text_short_64` | 155.7 ms | **943.1 ms** | **55.0 tok/s** | 1.30 GiB |
| 128 | `text_medium_128` | 230.4 ms | 3146.8 ms | 44.1 tok/s | 1.18 GiB |
| 256 | `text_medium_128` | 210.8 ms | 2595.9 ms | 54.0 tok/s | 2.24 GiB |
| 512 | `text_medium_128` | **192.8 ms** | **2528.6 ms** | **55.1 tok/s** | 1.42 GiB |

### 图像结果

| `-ub` | case | TTFT mean | TTFT p50 | TTFT p95 | E2E mean |
|---:|---|---:|---:|---:|---:|
| 128 | `image_short_64` | 38172.3 ms | 250.7 ms | 151949.7 ms | 39374.0 ms |
| 256 | `image_short_64` | 33050.5 ms | 257.6 ms | 131441.4 ms | 34323.0 ms |
| 512 | `image_short_64` | **29687.8 ms** | 253.5 ms | **117978.4 ms** | **30773.4 ms** |

### UBATCH sweep 结论

- 在当前设备与模型组合下，**`ub=512` 对文本中等输出最有利**；
- `ub=256` 与 `ub=512` 都明显优于 `ub=128`；
- `ub=512` 对图像的 **mean / p95** 也有改善，但**图像长尾仍然存在**；
- 因此在当前版本中，`ub=512` 是一个更值得保留的方向。

---

## 11. 最终性能结论

### 11.1 文本侧结论

当前版本已经可以给出比较明确的文本侧建议：

#### 若优先追求较短 E2E

推荐：

```text
-t 4 -tb 4 -ub 512
```

理由：

- `text_short_64` 的 E2E 已经降到 **943.1 ms**；
- `text_medium_128` 的 E2E 降到 **2528.6 ms**；
- decode 吞吐维持在 **约 55 tok/s**；
- 相比 `ub=128` 更稳定，也优于大部分其他组合。

#### 若优先追求更低 TTFT

可考虑：

```text
-t 4 -tb 6 -ub 256
```

理由：

- `text_short_64` TTFT 最低，为 **131.5 ms**；
- `text_medium_128` TTFT 最低，为 **165.8 ms**。

但该组合不是整体 E2E 最优，更适合强调“首 token 更快”的场景。

### 11.2 图像侧结论

图像侧结论比文本侧更重要，也更有工程价值：

1. **视觉路径 steady-state 并不差**，热态 p50 TTFT 大致在 **238~347 ms**；
2. **真正的问题是首个正式图像请求的超长尾**；
3. 即使在执行了 `image warmup` 之后，后续正式测试中仍然能观察到单次 **102~164 秒级** 的异常长尾；
4. 这说明当前 warmup 方案**没有完全复用正式图像请求的关键路径**，或者存在额外的视觉路径初始化 / cache 失效问题。

换句话说：

- 文本性能已经进入“参数调优阶段”；
- 图像性能仍然有一个必须单独优化的“首图长尾问题”。

---

## 12. 对图像长尾问题的当前判断

根据仓库中的 warmup 与正式结果，可以得到以下判断：

### 已确认的事实

- 冷启动首图约 **198.9 秒**；
- warmup 后 steady-state 图像请求可回到 **约 250 ms 级别 TTFT**；
- 但在 sweep 中，**首个正式图像请求**仍经常出现 **100 秒以上长尾**。

### 当前合理推断

这更像是以下问题之一，而不是单纯线程参数问题：

- warmup 请求与正式图像 case 虽然表面相似，但**服务端内部路径未完全复用**；
- 首个正式请求触发了额外的视觉相关初始化；
- warmup 后到正式 case 之间存在 cache 失效、上下文重建或资源回收；
- 图像路径的初始化收益没有稳定保留到后续正式请求。

### 当前阶段结论

**图像首个正式请求长尾问题仍需单独优化。**

当前版本的 README 不把它写成“已解决”，而是明确记录为：

- 已定位现象
- 已通过 benchmark 复现
- 已确认不是普通文本参数 sweep 就能解决的问题
- 后续应继续围绕视觉 warmup 路径与服务端复用机制排查

---

## 13. 关键工程问题与解决过程

## 13.1 Vulkan / GPU 路线编译与运行失败

现象包括：

- Vulkan 相关编译兼容问题
- compute pipeline 创建失败
- shader / driver 错误
- 段错误退出

结论：

- 这不是“命令写错”级别的问题；
- 更多是安卓 GPU 驱动、Vulkan 支持与量化 shader 的兼容性问题；
- 因此当前项目以 CPU 路线作为正式交付版本。

## 13.2 图像请求超出上下文长度

图像 base64 进入请求体后，实际 prompt token 会明显增大。项目中曾出现：

```text
request exceeds the available context size (2048 tokens)
```

解决方式：

- 将上下文从 `2048` 提升到 `8192`
- benchmark 与正式服务统一使用 `-c 8192`

## 13.3 模型陷入 `<think>` 而不给最终回答

现象：

- 请求返回正常
- 但一直输出 reasoning 内容
- 最终 `content` 为空或被 `max_tokens` 截断

解决方式：

```bash
--reasoning off
--reasoning-format none
```

这是当前移动端稳定交互的必要设置。

## 13.4 GGUF 文件路径 / 格式问题

项目中也遇到过：

```text
failed to read magic
```

这类问题最终说明：

- 路径可能指到了目录或错误文件
- 下载产物可能不完整
- 文件本身可能并非有效 GGUF

这类排查与 benchmark 同样重要，因为部署工程并不只是“调参数”。

---

## 14. 如何复现实验

### 14.1 启动服务

```bash
bash scripts/start_qwen_server.sh
```

### 14.2 文本 warmup

```bash
bash scripts/warmup.sh
```

### 14.3 图像 warmup

```bash
bash scripts/warmup_image.sh
```

### 14.4 执行 sweep

```bash
bash scripts/sweep_threads.sh
```

### 14.5 查看 summary

```bash
python src/benchmarks/report_summary.py \
  results/benchmark_runs/threads_sweep_20260401_215335/t4_tb4_ub512/text_medium_128.json
```

### 14.6 查看日志

```bash
bash scripts/watch_llama_log.sh
bash scripts/watch_web_log.sh
```

---

## 15. 项目价值总结

这个项目的价值不只是“在手机上跑通了一个模型”，而是完整覆盖了以下能力链路：

- 从服务端推理框架理解，过渡到端侧部署实践
- 从模型格式选择，走到 GGUF + llama.cpp 的真实落地
- 从单次调用验证，走到 OpenAI-compatible 服务封装
- 从手工体验，走到 benchmark 自动化
- 从能跑，走到可测、可比较、可解释
- 从部署成功，走到对性能瓶颈与未解决问题的清晰表述

对于大模型部署 / 推理加速方向来说，这比单纯演示“网页能聊天”更有工程含金量。

---

## 16. 后续优化方向

当前版本已经完成“部署 + 服务化 + 基准测试 + 参数调优”的第一阶段闭环。后续仍有三条明确优化线：

### 16.1 图像首个正式请求长尾优化

优先级最高。重点应放在：

- warmup 内容是否与正式 case 完全一致
- warmup 后服务是否真正复用了同一路径
- 是否需要连续多次 image warmup
- 是否存在视觉 cache 未稳定保留的问题

### 16.2 文本参数进一步细分

后续可以继续扩展：

- 不同 `PARALLEL` 配置
- 不同 `BATCH_SIZE`
- 文本并发下的 aggregate 吞吐对比
- 更长输出长度下的 decode 稳定性

### 16.3 结果可视化与报告化

当前结果已经结构化保存为 JSON，后续可以进一步：

- 自动生成 Markdown 报告
- 绘制 TTFT / E2E / TPS 曲线
- 输出不同参数组合的总表

---

## 17. 总结

这是一个以 **Android 手机本地部署多模态模型** 为起点，进一步扩展到 **OpenAI-compatible 服务化、自动化基准测试、参数 sweep、性能分析与问题定位** 的完整工程项目。

当前版本的结论清晰：

- **文本链路已经基本跑顺，并形成了可复用的参数调优结论；**
- **图像链路已经具备热态可用性，但首个正式请求长尾仍是下一阶段的核心优化目标。**

