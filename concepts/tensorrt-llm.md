---
aliases:
- trt-llm
tags:
- inference-framework
- nvidia
- optimization
- tensorrt
created: '2026-06-10'
---

# tensorrt-llm

## 定义

TensorRT-LLM 是 NVIDIA 推出的高性能 LLM 推理优化库，基于 TensorRT 深度学习推理引擎，针对 NVIDIA GPU 进行极致优化。

## 核心特性

### 1. 极致性能优化

#### Kernel Fusion
```
传统: 多个独立 kernel
  MatMul → Add → ReLU → MatMul
  4次 kernel launch, 3次内存访问

TensorRT-LLM: 融合 kernel
  Fused_Operation
  1次 kernel launch, 1次内存访问
```

#### Graph Optimization
- **Layer fusion**: 合并相邻层
- **Constant folding**: 预计算常量
- **Dead code elimination**: 移除无用计算

#### Memory Optimization
- **Memory pooling**: 复用内存
- **In-place operations**: 原地操作
- **Reduced precision**: FP16/INT8/INT4

### 2. Multi-GPU 支持

```python
# Tensor Parallelism
config.tensor_parallel = 4

# Pipeline Parallelism
config.pipeline_parallel = 2

# Total: 4 × 2 = 8 GPUs
```

### 3. 量化支持

**量化精度**:
- **FP16**: 2× 加速
- **INT8**: 4× 加速（W8A8）
- **INT4**: 8× 加速（AWQ/GPTQ）
- **FP8**: 2× 加速（H100）

## 架构设计

### 三层架构

```
┌─────────────────────────┐
│   Python API Layer       │  高级接口
├─────────────────────────┤
│   C++ Runtime            │  执行引擎
├─────────────────────────┤
│   TensorRT Core          │  优化内核
└─────────────────────────┘
```

### Engine Building
```
过程:
1. 模型定义（Python/ONNX）
2. 优化和编译
3. Engine 序列化
4. 部署推理

结果: .engine 文件（特定 GPU 优化）
```

## 性能表现

### 吞吐量对比

| 模型 | vLLM | TensorRT-LLM | 提升 |
|------|------|--------------|------|
| GPT-J-6B | 1200 tok/s | 2000 tok/s | 1.7× |
| LLaMA-7B | 950 tok/s | 1650 tok/s | 1.7× |
| LLaMA-70B | 180 tok/s | 320 tok/s | 1.8× |

### 延迟对比

| 场景 | vLLM | TensorRT-LLM | 降低 |
|------|------|--------------|------|
| Prefill (2K ctx) | 85ms | 45ms | 47% |
| Decode | 12ms | 7ms | 42% |

### 硬件利用率
```
GPU Utilization:
- vLLM: 65-75%
- TensorRT-LLM: 80-90%

Memory Efficiency:
- vLLM: Good
- TensorRT-LLM: Excellent
```

## 使用方法

### 模型转换
```python
from tensorrt_llm import Builder

# 1. 定义模型
builder = Builder()
builder.load_model("meta-llama/Llama-2-7b-hf")

# 2. 配置优化
builder.set_precision("fp16")
builder.set_max_batch_size(128)
builder.set_max_input_len(2048)
builder.set_max_output_len(512)

# 3. 编译 engine
engine = builder.build()
engine.save("llama-7b.engine")
```

### 推理部署
```python
from tensorrt_llm import Runtime

# 加载 engine
runtime = Runtime("llama-7b.engine")

# 推理
outputs = runtime.generate(
    prompts=["Hello, how are you?"],
    max_new_tokens=100,
    temperature=0.7
)
```

### Triton 集成
```python
# Triton Inference Server 后端
model_repo/
├── llama-7b/
│   ├── config.pbtxt
│   └── 1/
│       └── model.engine

# 启动服务
tritonserver --model-repository=model_repo
```

## 高级特性

### In-flight Batching
```
动态批处理:
- 请求到达即处理（类似 continuous batching）
- 自动调整批次大小
- 最大化 GPU 利用率
```

### KV Cache Reuse
```python
# 支持 prefix caching
config.enable_kv_cache_reuse = True

# 共享 system prompt
shared_prefix = "You are a helpful assistant."
```

### Multi-LoRA
```python
# 同时服务多个 LoRA 适配器
runtime.load_lora("adapter1.safetensors")
runtime.load_lora("adapter2.safetensors")

# 推理时指定
output = runtime.generate(
    prompt="...",
    lora_id="adapter1"
)
```

### Medusa Decoding
```python
# 推测解码加速
config.enable_medusa = True
config.num_medusa_heads = 4
```

## 与其他框架对比

### vs vLLM

| 特性 | vLLM | TensorRT-LLM |
|------|------|--------------|
| 性能 | 好 | **极致** |
| 易用性 | **易** | 中等 |
| 灵活性 | **高** | 中等 |
| 生态 | **丰富** | 成长中 |
| 硬件 | NVIDIA | **仅 NVIDIA** |
| 编译时间 | 无 | 需要（5-30min）|

**选择建议**:
- **极致性能**: TensorRT-LLM
- **快速原型**: vLLM
- **模型实验**: vLLM
- **生产部署**: TensorRT-LLM

### vs Text Generation Inference (TGI)

| 特性 | TGI | TensorRT-LLM |
|------|-----|--------------|
| 性能 | 中 | **高** |
| HuggingFace | **原生** | 需转换 |
| 量化 | GPTQ, AWQ | **全部** |
| 开箱即用 | **易** | 需配置 |

### vs SGLang

| 特性 | SGLang | TensorRT-LLM |
|------|--------|--------------|
| RadixAttention | **是** | KV Reuse |
| 结构化生成 | **强** | 基础 |
| 性能 | 好 | **更好** |
| 编程接口 | **DSL** | API |

## 部署场景

### 云端推理
```
场景: 高QPS服务
配置: 
- TensorRT-LLM + Triton
- Multi-GPU (TP/PP)
- FP16 或 INT8
效果: 最大化吞吐量
```

### 边缘部署
```
场景: Jetson/边缘设备
配置:
- TensorRT-LLM
- INT8/INT4 量化
- 小模型优化
效果: 低延迟推理
```

### 批量处理
```
场景: 离线批处理
配置:
- 大 batch size
- Pipeline parallelism
- FP16
效果: 最高吞吐量
```

## 最佳实践

### 1. Engine 优化
```python
# Profile 驱动优化
builder.enable_profiling = True

# 多配置选择最优
builder.add_optimization_profile(
    min_batch=1, opt_batch=32, max_batch=128
)

# 针对硬件优化
builder.target_gpu = "A100"  # 或 H100
```

### 2. 量化选择
```python
# FP16: 平衡（默认）
# INT8: 高吞吐，需校准
# INT4: 极致压缩（AWQ/GPTQ）
# FP8: H100 最佳

# 推荐流程:
# 1. FP16 baseline
# 2. INT8 如果精度可接受
# 3. INT4 如果内存受限
```

### 3. 批次大小
```python
# 平衡延迟和吞吐
batch_size = calculate_optimal_batch(
    gpu_memory,
    model_size,
    max_input_len,
    target_latency
)

# 动态批处理优先
use_inflight_batching = True
```

### 4. 多 GPU 配置
```python
# 单节点优先 TP
tensor_parallel = 4  # NVLink

# 跨节点用 PP
pipeline_parallel = 2  # InfiniBand

# 避免过度切分
avoid_too_many_stages = True
```

## 监控和调试

### 性能分析
```bash
# TensorRT profiling
trtexec --loadEngine=model.engine \
        --profilingVerbosity=detailed

# NVIDIA Nsight
nsys profile -o profile.qdrep \
     python inference.py
```

### 关键指标
```
- Throughput (tok/s)
- Latency (ms)
  - TTFT (Time To First Token)
  - TPOT (Time Per Output Token)
- GPU Utilization (%)
- Memory Usage (GB)
```

## 局限和挑战

### 1. 编译时间
- Engine building 需 5-30 分钟
- 更改配置需重新编译
- 权衡: 性能 vs 灵活性

### 2. 硬件锁定
- Engine 特定 GPU 优化
- 不同 GPU 需重新编译
- 限制: 部署灵活性

### 3. 模型支持
- 不是所有模型都支持
- 新模型需要适配
- 改进中: 社区贡献

### 4. 调试复杂
- C++ 底层实现
- 错误信息不够清晰
- 学习曲线: 陡峭

## 未来发展

### 量化技术
- FP4 支持
- 混合精度自动化
- 动态量化

### 分布式
- 自动并行策略搜索
- 异构硬件支持
- 弹性扩缩容

### 易用性
- 简化编译流程
- 更多模型支持
- 更好的错误提示

### 生态整合
- HuggingFace 直接支持
- LangChain 集成
- OpenAI API 兼容


## 相关概念

- [[vllm]]
- [[sglang]]
