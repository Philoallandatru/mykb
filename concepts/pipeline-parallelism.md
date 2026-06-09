---
aliases:
- model-parallelism
- pipeline-parallel
tags:
- distributed-inference
- parallelism
- scalability
created: '2026-06-10'
---

# pipeline-parallelism

## 定义

Pipeline Parallelism（流水线并行）是一种模型并行技术，将模型层按序切分到多个设备上，通过流水线方式并行处理多个micro-batch，提高设备利用率。

## 核心原理

### 朴素模型并行问题
```
传统方式（串行）:
GPU 0: Layer 0-25  [█████░░░░░░░░░░░] 空闲
GPU 1: Layer 26-50 [░░░░░█████░░░░░░] 空闲  
GPU 2: Layer 51-75 [░░░░░░░░░░█████░] 空闲
GPU 3: Layer 76-99 [░░░░░░░░░░░░░░█] 空闲

问题: 同时只有1个GPU工作，利用率25%
```

### Pipeline Parallelism 解决方案
```
流水线（并行）:
时间 →
GPU 0: [Batch1][Batch2][Batch3][Batch4]
GPU 1:        [Batch1][Batch2][Batch3][Batch4]
GPU 2:               [Batch1][Batch2][Batch3][Batch4]
GPU 3:                      [Batch1][Batch2][Batch3][Batch4]

优势: 4个GPU同时工作，利用率接近100%
```

## 实现方式

### GPipe (Google)
**特点**: 同步流水线
```python
# 将 batch 切分为 micro-batches
micro_batches = split(batch, num_micro_batches)

# Forward 阶段
for mb in micro_batches:
    for stage in pipeline_stages:
        mb = stage.forward(mb)

# Backward 阶段（反向）
for mb in reversed(micro_batches):
    for stage in reversed(pipeline_stages):
        mb = stage.backward(mb)
```

**优点**: 实现简单，内存友好
**缺点**: Bubble time（空闲时间）存在

### PipeDream (Microsoft)
**特点**: 异步流水线
```
Forward 和 Backward 交替:
GPU 0: [F1][F2][F3][B1][F4][B2][F5][B3]...
GPU 1:    [F1][F2][B1][F3][B2][F4][B3]...

异步: 不等所有 micro-batch forward 完成
```

**优点**: 更低 bubble time
**缺点**: 权重版本不一致

### 1F1B (One Forward One Backward)
**平衡方案**:
```
稳态执行:
每完成1个 Forward → 立即执行1个 Backward
保持内存稳定，降低 bubble
```

## 性能分析

### Bubble Time
**定义**: 流水线中 GPU 空闲等待的时间

**GPipe bubble ratio**:
```
Bubble = (num_stages - 1) / num_micro_batches

例子: 4 stages, 8 micro-batches
Bubble = 3/8 = 37.5%
```

**优化策略**:
- 增加 micro-batches: Bubble ↓
- 权衡: 内存占用 ↑

### 吞吐量
```
理想加速比 = num_stages (无bubble)
实际加速比 = num_stages × (1 - bubble_ratio)

例子: 4 GPUs, 8 micro-batches
实际 = 4 × (1 - 0.375) = 2.5×
```

### 内存占用
```
GPipe:
- Peak: num_micro_batches × activation_size
- 高内存占用

1F1B:
- Peak: 2 × activation_size
- 内存友好
```

## LLM 推理应用

### 超大模型推理
```
场景: 单 GPU 无法容纳完整模型
方案: Pipeline 切分层

示例: LLaMA-70B (80 layers)
GPU 0: Layer 0-19   (20 layers)
GPU 1: Layer 20-39  (20 layers)
GPU 2: Layer 40-59  (20 layers)
GPU 3: Layer 60-79  (20 layers)
```

### 批次处理
```
推理场景优化:
- 只需 Forward（无 Backward）
- Bubble 降低 50%
- 更适合批量推理
```

### 延迟 vs 吞吐量
```
单请求延迟:
  Pipeline: 高（需遍历所有 stage）
  Tensor: 低（所有 GPU 并行）

批量吞吐量:
  Pipeline: 高（流水线充分利用）
  Tensor: 中（通信开销）

适用: Pipeline 适合高吞吐场景
```

## 实现框架

### Megatron-LM
```python
from megatron import mpu

# 初始化 pipeline parallelism
mpu.initialize_model_parallel(
    tensor_model_parallel_size=1,
    pipeline_model_parallel_size=4
)

# 模型自动切分
model = GPTModel(
    num_layers=80,
    # 自动分配到 4 个 pipeline stages
)
```

### DeepSpeed
```python
from deepspeed import pipe

# 定义 pipeline stages
class LayerSpec:
    def __init__(self):
        self.layers = [
            LayerSpec(TransformerLayer, ...),
            LayerSpec(TransformerLayer, ...),
            # ...
        ]

# Pipeline engine
engine = pipe.PipelineEngine(
    model=model,
    stages=4,
    micro_batches=8
)
```

### vLLM (推理)
```bash
# vLLM 支持 pipeline parallelism
python -m vllm.entrypoints.openai.api_server   --model meta-llama/Llama-2-70b-hf   --tensor-parallel-size 2   --pipeline-parallel-size 2  # 2x2 = 4 GPUs
```

## 配置调优

### Micro-batch 数量
```python
# 权衡: bubble vs 内存
num_micro_batches = max(
    4 × num_stages,  # 降低 bubble
    memory_limit / activation_size  # 内存约束
)

# 推荐: 8-16 个 micro-batches
```

### Stage 切分
```python
# 均衡原则: 每个 stage 计算量相近
stage_size = total_layers / num_stages

# 考虑:
# - 层的计算复杂度
# - 激活值大小
# - 通信开销
```

### 通信优化
```python
# 重叠计算和通信
enable_async_communication = True

# P2P 通信（相邻 stage）
use_p2p_communication = True

# 压缩激活值
enable_activation_compression = False  # 推理通常不需要
```

## 与 Tensor Parallelism 对比

### 通信模式
```
Pipeline:
- 点对点（相邻 stage）
- 通信量: activation_size
- 频率: 每层一次

Tensor:
- All-Reduce（所有 GPU）
- 通信量: hidden_size × seq_len
- 频率: 每层两次
```

### 适用场景
```
Pipeline Parallelism:
✓ 跨节点部署（低带宽）
✓ 高吞吐批处理
✓ 层数很多的模型
✗ 低延迟推理
✗ 单请求处理

Tensor Parallelism:
✓ 节点内部署（NVLink）
✓ 低延迟推理
✓ 单请求处理
✗ 跨节点（通信开销大）
```

### 混合使用
```
2D Parallelism:
  节点内: Tensor Parallelism (NVLink)
  节点间: Pipeline Parallelism (InfiniBand)

示例: 8 nodes × 8 GPUs = 64 GPUs
  TP = 8 (节点内)
  PP = 8 (节点间)
```

## 工程挑战

### 1. 负载均衡
```
问题: 不同层计算量差异大
解决: 
- Profile 每层耗时
- 动态调整 stage 边界
- 考虑内存占用
```

### 2. Bubble 优化
```
策略:
- 增加 micro-batches
- 使用 1F1B 调度
- Interleaved pipeline (交错)
```

### 3. 内存管理
```
激活值存储:
- GPipe: 存储所有 micro-batches
- 1F1B: 仅存储 2 个
- Recomputation: 节省内存
```

### 4. 通信瓶颈
```
优化:
- 使用高速互联（InfiniBand）
- 压缩激活值（FP16 → BF16）
- 异步通信
```

## 监控和调试

### 关键指标
```python
# Bubble time
bubble_ratio = idle_time / total_time

# 吞吐量
throughput = samples_per_second

# 负载均衡
stage_times = [t0, t1, t2, t3]
imbalance = max(stage_times) / mean(stage_times)
```

### 可视化
```
Timeline:
GPU 0: ████░░██░░██░░██
GPU 1: ░░████░░██░░██░░
GPU 2: ░░░░████░░██░░██
GPU 3: ░░░░░░████░░██░░

工具: NVIDIA Nsight Systems, TensorBoard
```

## 未来方向

### 自适应流水线
- 动态调整 micro-batch 大小
- 根据负载自动重平衡

### 异构流水线
- 不同 stage 不同硬件
- CPU + GPU 混合

### 弹性流水线
- 运行时增减 stage
- 容错和故障恢复


## 相关概念

- [[tensor-parallelism]]
- [[distributed-inference]]
