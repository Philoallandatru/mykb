---
aliases:
- ggml
- llama-cpp-format
tags:
- model-format
- quantization
- cpu-inference
- edge-deployment
created: '2026-06-10'
---

# gguf

## 定义

GGUF (GPT-Generated Unified Format) 是 llama.cpp 项目开发的模型文件格式，专为 CPU 和边缘设备的高效 LLM 推理设计，支持量化和快速加载。

## 背景和演进

### 格式历史
```
GGML (2023.3) → GGMF → GGJT → GGUF (2023.8)

改进:
- 更好的元数据支持
- 版本兼容性
- 扩展性
- 标准化
```

### 设计目标
- **CPU 友好**: 优化 CPU 推理
- **量化支持**: 多种量化精度
- **快速加载**: mmap 支持
- **跨平台**: Windows/Linux/macOS/Mobile
- **边缘部署**: 低内存占用

## 文件结构

### GGUF 格式布局
```
┌─────────────────────────┐
│  Header                 │  版本、对齐信息
├─────────────────────────┤
│  Metadata (KV pairs)    │  模型配置、分词器
├─────────────────────────┤
│  Tensor Info            │  张量元数据
├─────────────────────────┤
│  Padding (alignment)    │  对齐到 32 bytes
├─────────────────────────┤
│  Tensor Data            │  量化权重数据
└─────────────────────────┘
```

### 元数据示例
```python
metadata = {
    "general.name": "LLaMA-2-7B",
    "general.architecture": "llama",
    "llama.context_length": 4096,
    "llama.embedding_length": 4096,
    "llama.attention.head_count": 32,
    "tokenizer.ggml.model": "llama",
    # ... 更多配置
}
```

## 量化支持

### 量化类型

| 类型 | Bits | 压缩比 | 精度 | 速度 | 推荐场景 |
|------|------|--------|------|------|----------|
| F32 | 32 | 1× | 最高 | 慢 | Baseline |
| F16 | 16 | 2× | 高 | 中 | GPU推理 |
| Q8_0 | 8 | 4× | 高 | 快 | 平衡 |
| Q6_K | 6 | 5.3× | 好 | 快 | 推荐 |
| Q5_K | 5 | 6.4× | 中 | 快 | 常用 |
| Q4_K | 4 | 8× | 中 | 很快 | 常用 |
| Q3_K | 3 | 10.7× | 低 | 很快 | 极致压缩 |
| Q2_K | 2 | 16× | 很低 | 最快 | 实验性 |

### K-Quants 说明
```
K-Quants (Q4_K, Q5_K, Q6_K):
- 混合量化策略
- 重要层高精度
- 次要层低精度
- 平衡精度和大小

结果: 优于均匀量化
```

### 量化方法
```python
# llama.cpp 转换工具
./convert.py llama-2-7b-hf/

# 量化
./quantize llama-2-7b-f16.gguf \
           llama-2-7b-q4_k_m.gguf Q4_K_M

# 变体:
# Q4_K_S: Small (更小)
# Q4_K_M: Medium (平衡)
# Q4_K_L: Large (更精确)
```

## 性能特征

### 内存占用
```
LLaMA-7B:
- FP32: 28 GB
- FP16: 14 GB
- Q8_0: 7.5 GB
- Q6_K: 5.5 GB
- Q5_K: 5 GB
- Q4_K: 4 GB
- Q3_K: 3.5 GB

适用设备:
- 32GB RAM: Q4/Q5 (7B-13B)
- 16GB RAM: Q4 (7B)
- 8GB RAM: Q4 (3B)
```

### CPU 推理速度
```
硬件: M2 Pro (12 cores)
模型: LLaMA-7B Q4_K_M

性能:
- Prompt: ~50 tok/s
- Generate: ~15 tok/s
- 内存: ~5 GB

对比 GPU:
- RTX 4090: ~120 tok/s
- 但 CPU 更易获得
```

### 精度损失
```
困惑度 (LLaMA-7B):
- FP16: 5.68
- Q8_0: 5.70 (+0.02)
- Q6_K: 5.72 (+0.04)
- Q5_K: 5.75 (+0.07)
- Q4_K: 5.85 (+0.17)
- Q3_K: 6.15 (+0.47)

推荐: Q4_K/Q5_K (性价比最高)
```

## 使用方法

### llama.cpp
```bash
# 编译
git clone https://github.com/ggerganov/llama.cpp
make

# 运行
./main -m llama-2-7b-q4_k_m.gguf \
       -p "Once upon a time" \
       -n 256 \
       -t 8  # 线程数
```

### Python 绑定 (llama-cpp-python)
```python
from llama_cpp import Llama

llm = Llama(
    model_path="llama-2-7b-q4_k_m.gguf",
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=0  # CPU only
)

output = llm(
    "Q: What is AI? A:",
    max_tokens=128,
    temperature=0.7
)
print(output['choices'][0]['text'])
```

### 服务器模式
```bash
# 启动 API 服务
./server -m llama-2-7b-q4_k_m.gguf \
         --host 0.0.0.0 \
         --port 8080 \
         -t 8

# OpenAI 兼容 API
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 50}'
```

## GPU 加速

### Metal (macOS)
```bash
# M1/M2/M3 GPU 加速
make LLAMA_METAL=1

./main -m model.gguf -ngl 32  # offload 32 layers
```

### CUDA (NVIDIA)
```bash
# CUDA 编译
make LLAMA_CUBLAS=1

./main -m model.gguf -ngl 40  # offload to GPU
```

### Vulkan (跨平台)
```bash
# Vulkan 支持
make LLAMA_VULKAN=1
```

### 混合推理
```python
llm = Llama(
    model_path="model.gguf",
    n_gpu_layers=20,  # 前 20 层在 GPU
    # 其余层在 CPU
)

# 平衡延迟和资源
```

## 优化技术

### mmap (内存映射)
```c
// GGUF 设计支持 mmap
// 不加载整个模型到内存
// 按需分页加载

优势:
- 快速启动 (< 1秒)
- 低内存占用
- 多进程共享

// llama.cpp 自动使用 mmap
```

### SIMD 优化
```c
// ARM NEON
// x86 AVX2/AVX512
// 向量化计算

加速:
- 矩阵乘法
- 量化/反量化
- Softmax

结果: 2-4× CPU 加速
```

### 多线程
```bash
# 最优线程数 = 物理核心数
./main -m model.gguf -t $(nproc)

# 性能核优先 (大小核架构)
taskset -c 0-7 ./main ...
```

## 与其他格式对比

### vs PyTorch (.bin, .safetensors)
```
GGUF:
✓ 量化支持完善
✓ CPU 优化
✓ 快速加载
✗ 仅推理

PyTorch:
✓ 训练支持
✓ 生态完善
✗ CPU 推理慢
✗ 内存占用大
```

### vs ONNX
```
GGUF:
✓ LLM 专用优化
✓ 量化更灵活
✓ 更小文件

ONNX:
✓ 跨框架
✓ 硬件支持广
✗ LLM 支持有限
```

### vs TensorRT Engine
```
GGUF:
✓ CPU 友好
✓ 简单部署
✗ GPU 性能一般

TensorRT:
✓ GPU 极致性能
✗ NVIDIA 专属
✗ CPU 不支持
```

## 应用场景

### 1. 边缘设备
```
场景: 树莓派、手机、嵌入式

配置:
- 模型: Q4_K/Q3_K
- 大小: 3-7B
- 内存: 4-8GB

应用:
- 本地助手
- 离线翻译
- 私密 AI
```

### 2. 桌面应用
```
场景: 个人电脑本地运行

配置:
- 模型: Q4_K/Q5_K
- 大小: 7-13B
- 内存: 16-32GB

应用:
- 写作助手
- 代码补全
- 本地 RAG
```

### 3. 服务器推理
```
场景: CPU 服务器批量推理

配置:
- 模型: Q6_K/Q8_0
- 大小: 13-70B
- 内存: 64GB+

应用:
- 批量处理
- 成本优化
- GPU 补充
```

### 4. 移动应用
```
场景: iOS/Android App

配置:
- 模型: Q4_K
- 大小: 1-3B
- 内存: 2-4GB

框架:
- llama.cpp mobile
- MLC LLM
```

## 生态系统

### 工具
```
转换:
- convert.py (HF → GGUF)
- quantize (量化)

推理:
- llama.cpp (C++)
- llama-cpp-python (Python)
- llama.cpp server (API)

应用:
- Ollama (易用性)
- LM Studio (GUI)
- GPT4All (开源套件)
```

### 模型库
```
HuggingFace:
- TheBloke/* (大量 GGUF 模型)
- 预量化模型
- 开箱即用

示例:
- TheBloke/Llama-2-7B-GGUF
- TheBloke/Mistral-7B-Instruct-GGUF
```

## 最佳实践

### 1. 量化选择
```
内存充足: Q6_K/Q5_K (高精度)
内存有限: Q4_K (平衡)
极限压缩: Q3_K (可接受损失)

避免: Q2_K (精度太差)
```

### 2. 性能调优
```bash
# 物理核心数
threads=$(lscpu | grep "Core(s) per socket" | awk '{print $4}')

# NUMA 绑定 (多socket)
numactl --cpunodebind=0 --membind=0 ./main ...

# 大页支持
echo 2048 > /proc/sys/vm/nr_hugepages
```

### 3. 内存优化
```
启用 mmap: 默认开启
锁定内存: --mlock (避免 swap)
预分配: --no-mmap (稳定性优先)
```

### 4. 批处理
```python
# 批量推理降低延迟
prompts = [...]
for prompt in prompts:
    llm(prompt)  # 复用加载的模型
```

## 未来发展

### GGUF 改进
- 更低精度量化 (1-bit)
- 专家混合 (MoE) 支持
- 更好的元数据

### llama.cpp 发展
- 更多硬件后端
- 更快推理引擎
- 分布式支持

### 生态扩展
- 更多框架集成
- 工具链完善
- 社区贡献


## 相关概念

- [[awq]]
- [[gptq]]
- [[model-compression]]
