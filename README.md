# Android 手机端多模态模型部署实战：Qwen3.5-0.8B + llama.cpp + Termux

> 一个面向**推理加速 / 模型部署岗位**的真实工程项目记录。  
> 目标是**把模型部署到安卓手机本地，以服务形式提供调用**，并沉淀完整的环境搭建、踩坑、定位和取舍过程。

---

## 1. 项目简介

本项目分为两条主线：

- **服务端主线**：笔记本侧使用 `vLLM + FastAPI + Web` 跑通本地推理服务，并实现电脑 / 手机同一局域网网页访问。
- **端侧主线**：安卓手机侧使用 `Termux + llama.cpp + GGUF` 在本地部署多模态模型，并通过 `llama-server` 暴露本地 HTTP 接口，实现：
  - 纯文本聊天
  - 图片上传分析
  - 本地网页 / 脚本调用

本项目最终目标：

1. 能完成从模型格式选择、运行时选型、服务启动到接口调用的完整链路；
2. 能解释不同推理框架的适用场景；
3. 能在真实设备上处理部署中的兼容性、推理稳定性和性能取舍问题。

---

## 2. 为什么做这个项目

我的求职目标是：

- AI Infra / 推理加速方向实习大模型部署工程师

因此项目重点不是 UI，也不是花哨功能，而是：

- 推理框架选型
- 服务化封装
- 模型格式适配
- 移动端可复现部署
- 问题定位与工程取舍

整个项目始终坚持一个原则：**稳定、可复现、可解释 **

---

## 3. 技术路线选择

### 3.1 为什么笔记本端用 vLLM

笔记本端目标是先跑通一个典型的服务端推理系统，因此采用：

- `vLLM`：做模型推理服务
- `FastAPI`：做 API 服务层
- `HTML/JS`：做简单前端页面

这一阶段重点是理解：

- 本地模型服务如何启动
- OpenAI-compatible API 如何调用
- 文本 / 文件 / 图片三类输入如何组织

### 3.2 为什么手机端不用 vLLM / LMDeploy，而改用 llama.cpp

手机端目标已经不是高吞吐服务，而是：

- 端侧本地部署
- 资源受限环境运行
- 本地 HTTP 服务调用

因此最终选择：

- `llama.cpp`：轻量推理引擎
- `GGUF`：移动端更友好的模型格式
- `Termux`：把安卓手机变成一个可操作的 Linux 风格环境
- `llama-server`：提供本地 HTTP 接口

---

## 4. 最终项目形态

### 4.1 笔记本端项目结构

```text
test_code/
├─ fastapi_server/
│  ├─ main.py
│  ├─ config.py
│  ├─ services/
│  │  └─ vllm_client.py
│  ├─ web/
│  │  └─ index.html
│  ├─ uploads/
│  └─ logs/
├─ scripts/
│  ├─ start_vllm.sh
│  ├─ start_fastapi.sh
│  └─ test_curl.sh
└─ README.md
```

### 4.2 手机端项目结构

```text
mobile_llm/
├── llama.cpp/
├── models/
│   └── Qwen_Qwen3.5-0.8B-Q4_K_M/
│       ├── Qwen3.5-0.8B-Q4_K_M.gguf
│       └── mmproj-F16.gguf
├── scripts/
│   ├── start_server.sh
│   ├── warmup.sh
│   ├── test_text.sh
│   ├── test_image.py
│   └── start_web.sh
├── web_demo/
│   └── index.html
└── venvs/
    └── modelscope_env/
```

---

## 5. 笔记本端：

- 移步仓库：https://github.com/zxy159632/-vLLM-FastAPI-

---

## 6. 手机端：

不满足于“手机只是前端，电脑在推理”，而是进一步做了：

> **将模型部署到安卓手机本地，并以服务方式提供调用。**

最终服务接口形态：

```text
http://127.0.0.1:8081/v1/chat/completions
```

这样后续无论是：

- 浏览器网页
- Python 脚本
- 自己写的 Android App

本质上都可以调用同一个本地服务。

---

## 7. 手机端完整流程

### 7.1 前期准备

设备与环境：

- 手机：Redmi K90（12GB + 256GB）
- Android 端安装：`Termux`
- 网络辅助：通过网页版 `code-server` 连接手机 Termux，方便编辑脚本和源码

### 7.2 手机联通与远程编辑

在 Termux 中执行：

```bash
pkg update
pkg upgrade
termux-wake-lock
pkg install openssh
sshd
ifconfig
passwd
whoami
pkg install tur-repo -y
pkg install code-server -y
```

然后修改 `~/.config/code-server/config.yaml` 中的监听地址为 `0.0.0.0:8080`，再执行：

```bash
code-server --bind-addr 0.0.0.0:8080
```

电脑浏览器访问：

```text
http://手机IP:8080/
```

这样就能在电脑浏览器里编辑手机上的文件，大幅提升开发效率。

---

## 8. 模型选择与格式适配

### 8.1 为什么不用现有 AutoRound 模型文件直接上手机

我在笔记本端使用过 `Qwen3.5-0.8B-int4-AutoRound` 跑 vLLM，这对服务端实验很好用；但端侧运行时和服务端运行时并不完全相同。

手机端最终采用的是 **GGUF 格式模型**，原因是：

- `llama.cpp` 原生支持 GGUF
- GGUF 更适合资源受限设备的本地推理
- 更适合在端侧快速搭建 CLI 和 HTTP 服务

### 8.2 最终采用的模型

前期通过 ModelScope 下载第三方模型文件：

```bash
modelscope download \
  --model Manojb/Qwen_Qwen3.5-0.8B-Q4_K_M.gguf \
  --local_dir ~/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M
```

后续又替换为更规范的一组官方 / 主流社区文件：

```bash
modelscope download --model unsloth/Qwen3.5-0.8B-GGUF --include "Qwen3.5-0.8B-Q4_K_M.gguf" --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M
modelscope download --model unsloth/Qwen3.5-0.8B-GGUF --include "mmproj-F16.gguf" --local_dir /data/data/com.termux/files/home/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M
```

最终手机端主演示采用：

- `Qwen3.5-0.8B-Q4_K_M.gguf`
- `mmproj-F16.gguf`

三方模型也调通了，但面试与演示以文件命名更规范的版本为主。

---

## 9. 手机端环境搭建

### 9.1 基础工具安装

```bash
pkg install -y git cmake clang make python wget curl
pkg install -y ninja
```

### 9.2 创建目录

```bash
mkdir -p ~/zxy/mobile_llm/models
mkdir -p ~/zxy/mobile_llm/scripts
mkdir -p ~/zxy/mobile_llm/venvs
```

### 9.3 独立 Python 环境

手机端没有强行折腾 conda，而是采用更稳的 `venv`：

```bash
python -m venv ~/zxy/mobile_llm/venvs/modelscope_env
source ~/zxy/mobile_llm/venvs/modelscope_env/bin/activate
pip install -U pip setuptools wheel
pip install -U modelscope
```

这里的工程取舍是：

- **目标是快速稳定完成部署**，不是在手机上复刻 PC 端一整套发行版级包管理；
- 对于下载模型这类 Python 任务，`venv` 足够满足隔离需求；
- `llama.cpp` 的编译与运行则保持原生 Termux 路线，更稳。

---

## 10. 编译 llama.cpp

### 10.1 CPU 版本先跑通

```bash
cd ~/zxy/mobile_llm
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp

cmake -B build
cmake --build build -j 4
```

如果手机性能或温度压力较大，则降为：

```bash
cmake --build build -j 2
```

### 10.2 检查产物

```bash
ls -lh build/bin
```

理想情况下至少看到：

- `llama-cli`
- `llama-server`

---

## 11. CLI 验证：先证明模型能跑

在真正起服务前，先用 CLI 做最小验证：

```bash
MODEL_DIR="$HOME/zxy/mobile_llm/models/Qwen_Qwen3.5-0.8B-Q4_K_M"
MODEL_FILE=$(find "$MODEL_DIR" -maxdepth 1 -name "*.gguf" ! -name "mmproj*" | head -n 1)
MMPROJ_FILE=$(find "$MODEL_DIR" -maxdepth 1 -name "mmproj*.gguf" | head -n 1)

./build/bin/llama-cli \
  -m "$MODEL_FILE" \
  -p "请用三句话介绍一下 Transformer。"
```

如果这一步能正常输出，说明：

- GGUF 主模型没问题
- `llama.cpp` 编译成功
- 手机 CPU 路线基本打通

---

## 12. 启动手机本地服务

### 12.1 最小启动命令

```bash
./build/bin/llama-server \
  -m "$MODEL_FILE" \
  --mmproj "$MMPROJ_FILE" \
  --host 127.0.0.1 \
  --port 8081 \
  -c 2048
```

### 12.2 文本请求验证

```bash
curl http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3.5-0.8B",
    "messages": [
      {
        "role": "user",
        "content": "请用三句话介绍 KV Cache 的作用。"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 128
  }'
```

### 12.3 图片请求验证

先把图片转为 base64，再构造 OpenAI Vision 风格请求。

---

## 13. 图片分析链路

### 13.1 图片位置

手机拍照后的图片通常位于：

```text
/storage/emulated/0/DCIM/Camera/test.jpg
```

在 Termux 中拿到存储权限：

```bash
termux-setup-storage
```

### 13.2 图片转 base64

```bash
base64 -w 0 ~/storage/shared/DCIM/Camera/test.jpg > ~/zxy/mobile_llm/test_image.b64
```

若 `-w 0` 不支持，则改用 Python。

### 13.3 发送图片请求

```bash
IMG_B64=$(cat ~/zxy/mobile_llm/test_image.b64)

curl http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\
    \"model\": \"Qwen3.5-0.8B\",\
    \"messages\": [\
      {\
        \"role\": \"user\",\
        \"content\": [\
          {\
            \"type\": \"text\",\
            \"text\": \"请描述这张图片的主要内容，并尽量简洁。\"\
          },\
          {\
            \"type\": \"image_url\",\
            \"image_url\": {\
              \"url\": \"data:image/jpeg;base64,$IMG_B64\"\
            }\
          }\
        ]\
      }\
    ],\
    \"temperature\": 0.2,\
    \"max_tokens\": 128\
  }"
```

同时保留了一个更稳的 `test_image.py` 脚本，避免 shell 拼接过长 JSON 时出错。

---

## 14. 我遇到的主要问题，以及如何解决

这一部分是本项目最重要的工程价值之一。

### 问题 1：新版 llama.cpp Vulkan 编译报错

报错示例：

```text
error: no viable overloaded '='
```

定位到：

```text
llama.cpp/ggml/src/ggml-vulkan/ggml-vulkan.cpp
```

对应代码使用了某段初始化写法，在当前环境下不兼容。

#### 处理方式
将 `device_create_info = { ... }` 改成链式 `.setFlags() / .setQueueCreateInfos()` 的写法后重新编译。

#### 工程结论
这类问题说明：

- 手机端部署不是“下个模型就跑”；
- 运行时、系统头文件、Vulkan C++ 封装版本之间会出现兼容问题；
- 阅读和修改少量 C++ 源码是部署岗位必须具备的能力之一。

---

### 问题 2：Vulkan GPU 路线启动时 shader / pipeline 崩溃

报错示例：

```text
Compute pipeline creation failed for mul_mat_vec_q6_k_f32_f32
vk::Device::createComputePipeline: ErrorUnknown
Segmentation fault
```

#### 初始困惑
我下载的是 `Q4_K_M` 模型，为什么错误里会出现 `q6_k`？

#### 原因分析
`Q4_K_M` 这类 K 系列量化并不是“纯 4bit 到底”，而是为了平衡精度，会在某些关键层混合使用 Q5_K / Q6_K 等内部数据表示。电脑 GPU 驱动一般能较好支持这类混合精度 shader，但安卓手机 GPU 驱动在这方面成熟度明显弱很多，于是就出现了 shader 编译失败、底层驱动崩溃、服务段错误退出等问题。

#### 工程结论
- **不是模型坏了，也不是命令写错了**；
- 问题更偏底层驱动与运行时兼容；
- GPU 路线我已经完整尝试并定位到“驱动 / shader 兼容性”层面；
- 当前阶段不再继续死磕现场 GPU 演示，而是把 GPU 路线作为“研究过并能解释”的补充材料。

---

### 问题 3：更换 `Q4_0` 模型后出现 `failed to read magic`

报错示例：

```text
gguf_init_from_file_impl: failed to read magic
llama_model_load_from_file_impl: failed to load model
```

#### 原因分析
GGUF 文件头前几个字节必须是 `GGUF` 魔数。出现这个错误通常意味着：

- 文件本身不是合法 GGUF；
- 路径指向错了（可能指到目录或错误文件）；
- 下载产物不完整。

#### 工程结论
部署工程里，**文件路径、格式校验、模型来源可靠性** 都必须纳入排查流程，而不是只盯着推理命令。

---

### 问题 4：模型一直陷入 `<think>`，回答不出最终内容

现象：

- 请求能收到返回；
- 但模型一直在输出 `reasoning_content`；
- `content` 为空，最终因为 `max_tokens` 不够而截断。

#### 原因分析
Qwen3.5 这一类模型 / 模板组合在 `llama.cpp` 当前 reasoning 机制下，可能默认进入思考模式。再叠加某些模板处理方式，就容易出现“长时间停留在 `<think>` 阶段”的情况。

#### 处理方式
启动服务时显式关闭 reasoning：

```bash
./build/bin/llama-server \
  -m "$MODEL_FILE" \
  --mmproj "$MMPROJ_FILE" \
  --host 127.0.0.1 \
  --port 8081 \
  -c 2048 \
  --reasoning off \
  --reasoning-format none
```

#### 工程结论
为了保证移动端交互稳定性，当前版本默认关闭 reasoning；reasoning 模式仅作为调试用途保留。

---

### 问题 5：图片请求超过上下文长度

现象：

- 文本请求正常；
- 图片请求报 token 超限，或者明显更慢。

#### 原因分析
图片转 base64 后体积很大，多模态模板也会额外占用上下文。

#### 处理方式
- 前端或脚本侧先压缩图片；
- 启动服务时适当增大 `-c`；
- 尽量用短 prompt；
- 不做长篇图片问答。

---

## 15. 为什么最终演示主线采用 CPU，而不是 GPU

这是一个我刻意做出的工程取舍。

### 原因
1. GPU 路线确实跑通过流程，但在安卓手机上存在明显驱动和 shader 兼容性风险；
2. 面试现场更需要“稳”，而不是赌运气；
3. CPU 路线虽然慢一些，但足够支撑：
   - 纯文本聊天演示
   - 图片分析演示
   - 本地 HTTP 服务调用展示

### 结论
- **GPU 路线：保留为问题分析材料**
- **CPU 路线：作为稳定、可复现、可演示的主线方案**

这是一个很典型的部署工程判断：

> 并不是所有“能跑的配置”都适合做最终交付方案。

---

## 16. 这个项目锻炼了哪些能力

### 能力 1：推理框架选型能力
能够根据场景区分：

- 服务端高吞吐：`vLLM`
- 端侧本地部署：`llama.cpp`

### 能力 2：模型格式与运行时适配能力
- 服务端可用的量化格式不一定适合手机端运行时；
- 手机端需要考虑 GGUF、`mmproj`、运行时兼容性；
- 模型部署不是“下载即运行”，而是“模型格式、运行时、系统环境三者匹配”。

### 能力 3：服务化思维
不是只会命令行本地生成，而是把手机端模型进一步做成了：

- 本地 HTTP 服务
- 标准 JSON 请求
- 文本 / 图片两类调用路径
- 后续可接网页和 Android App

### 能力 4：问题定位与工程取舍能力
项目过程中不是一路顺滑，而是经历了：

- Vulkan 编译问题
- GPU shader 崩溃
- 模型格式校验错误
- reasoning 模式卡死
- 图片上下文过长

不仅能记录问题，还能给出：

- 原因分析
- 排查路径
- 最终取舍

---

## 17. 项目不足与后续优化方向

### 当前不足
1. 手机端当前主线仍以 CPU 为主，性能上不如理想 GPU 路线；
2. 文件分析仍是“文件转文本再发给模型”的第一阶段方案；
3. 还没有完全封装成原生 Android App；
4. 还没有做系统化 benchmark 表格。

### 后续方向
1. 继续研究安卓 GPU / Vulkan 兼容性问题；
2. 将本地服务进一步封装为 Android App；
3. 增加更多稳定脚本与日志；
4. 补充端侧延迟、tokens/s、温度、功耗等指标记录；
5. 与笔记本侧 `vLLM + FastAPI` 项目形成对比，构成“服务端部署 + 端侧部署”双项目组合。

---

## 18. 一句话总结项目

> 完成了从笔记本侧 `vLLM + FastAPI` 本地推理服务，到安卓手机侧 `Termux + llama.cpp + GGUF + llama-server` 本地服务化部署的完整链路，并在真实设备上完成了文本聊天与图片分析调用，同时沉淀了模型格式适配、运行时选型、兼容性排查和稳定性取舍的工程经验。

---


## 19. 说明

本 README 不是“成功学复盘”，而是完整记录：

- 如何一步步把链路跑通的；
- 在哪些地方碰壁；
- 如何判断哪些问题该继续深挖，哪些问题该先绕开；
- 为什么最终选择了一个更稳、更适合展示和交付的方案。

如果你也在做手机端模型部署，希望这份记录能帮你少走一些弯路。

