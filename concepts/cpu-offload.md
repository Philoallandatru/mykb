---
aliases:
- cpu-memory-offload
- parameter-offloading
tags:
- offloading
- memory-management
- optimization
created: '2026-06-09'
---

# cpu-offload

## 定义

CPU Offload 是将 GPU 上的模型参数、激活值或 KV cache 卸载到 CPU 主内存的技术，用于处理 GPU 显存不足或支持超大规模模型推理的场景。

## 背景和动机

### GPU 显存限制
- **A100 (80GB)**: 无法容纳 175B+ 模型
- **消费级 GPU (24GB)**: 只能运行 7B 以下模型
- **KV Cache**: 长上下文或大批次快速耗尽显存

### CPU 内存优势
- **容量大**: 数百 GB - TB 级别
- **成本低**: 相比 GPU 显存便宜 10-20 倍
- **灵活性**: 易于扩展

### 权衡
- **延迟增加**: PCIe 传输 + CPU 计算慢
- **带宽限制**: PCIe 4.0 x16 ~64 GB/s vs HBM 2TB/s
- **复杂度**: 需要精心设计 offload 策略

## Offload 策略

### 1. 模型参数 Offload

#### 静态 Offload
```
模型层分布:
GPU: [Layer 0-10]      # 频繁使用
CPU: [Layer 11-79]     # 按需加载
```

**适用场景**:
- 推理时顺序执行
- 可预测访问模式
- 批次大小小

**实现**:
```python
# DeepSpeed ZeRO-Inference 示例
model = AutoModel.from_pretrained(
    "bigscience/bloom-176b",
    device_map="auto",  # 自动分配 GPU/CPU
    offload_folder="offload",
)
```

#### 动态 Offload
```
运行时决策:
if GPU_memory_low:
    offload_layer(least_recently_used_layer)
if layer_needed:
    load_from_CPU(layer)
```

**适用场景**:
- 不可预测访问模式
- 多任务并发
- 动态批次大小

### 2. KV Cache Offload

#### 场景
- **长上下文**: 2M token 上下文
- **大批次**: 批次 > 128
- **多会话**: 同时服务数百个会话

#### 策略

**分层存储**:
```
热数据 (最近N个token):
  GPU HBM (40GB)
  
温数据 (最近1000个token):
  CPU Memory (256GB)
  
冷数据 (历史全部):
  SSD (2TB)
```

**LRU淘汰**:
- 淘汰最久未使用的 KV cache
- 需要时从 CPU/SSD 加载

### 3. 激活值 Offload

#### Checkpoint 技术
```
Forward 阶段:
  计算激活 → offload 到 CPU → 释放 GPU 内存

Backward 阶段:
  从 CPU 加载 → 重计算 → 计算梯度
```

**权衡**:
- 内存换计算
- 适用于训练，推理较少使用

## 性能优化

### 1. 异步传输

#### Overlap 计算和传输
```python
# 伪代码
async def forward_with_offload():
    # 预取下一层
    future_layer = async_load_from_CPU(layer_id + 1)
    
    # 计算当前层
    output = current_layer.forward(input)
    
    # 等待预取完成
    next_layer = await future_layer
    
    return output
```

**收益**:
- 隐藏 PCIe 传输延迟
- 提升 20-40% 吞吐量

### 2. 压缩传输

#### 量化
- **传输**: INT8/INT4
- **计算**: 反量化到 FP16
- **收益**: 2-4× 带宽节省

#### 压缩
- **Lossless**: zstd, lz4
- **适用**: 稀疏激活
- **收益**: 1.5-3× 压缩比

### 3. 批量传输

#### 合并小传输
```
坏: 多次小传输 (延迟主导)
  Transfer(1MB) × 100 = 10ms × 100 = 1s

好: 一次大传输 (带宽主导)
  Transfer(100MB) = 200ms
```

## 硬件考量

### PCIe 带宽

| PCIe 版本 | 带宽 (x16) | 延迟 | 适用性 |
|-----------|-----------|------|--------|
| PCIe 3.0 | ~32 GB/s | ~10μs | 勉强可用 |
| PCIe 4.0 | ~64 GB/s | ~8μs | 可用 |
| PCIe 5.0 | ~128 GB/s | ~5μs | 较好 |
| PCIe 6.0 | ~256 GB/s | ~3μs | 理想 |

### NVLink vs PCIe

**NVLink**:
- GPU-GPU: 300-900 GB/s
- 延迟: < 1μs
- 用途: GPU 间通信

**PCIe**:
- GPU-CPU: 64-128 GB/s
- 延迟: 5-10μs
- 用途: CPU offload

### CXL (Compute Express Link)

**新兴技术**:
- **带宽**: 64-128 GB/s (CXL 2.0/3.0)
- **延迟**: < PCIe
- **优势**: 缓存一致性，统一内存空间
- **状态**: 2024-2025 开始商用

## 实现框架

### 1. DeepSpeed ZeRO-Inference

**特性**:
- 自动模型切分
- CPU offload
- NVMe offload

```python
from deepspeed import init_inference

model = init_inference(
    model,
    mp_size=1,
    dtype=torch.float16,
    offload=True,  # CPU offload
    offload_device="cpu"
)
```

### 2. FlexGen

**特性**:
- 4层内存层次 (GPU/CPU/Disk/Network)
- 自适应 offload 策略
- 支持超大模型 (175B+)

**策略**:
```
GPU (40GB):
  - 部分参数
  - 当前 batch 激活

CPU (256GB):
  - 大部分参数
  - KV cache

Disk (2TB):
  - 完整模型备份
  - 历史 KV cache
```

### 3. Hugging Face Accelerate

**device_map**:
```python
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "bigscience/bloom-176b",
    device_map="auto",  # 自动分配
    max_memory={
        0: "40GB",  # GPU 0
        "cpu": "200GB"
    }
)
```

## 性能数据

### 延迟影响

**模型参数加载**:
- 1GB 参数: ~15-30ms (PCIe 4.0)
- 影响: 每层增加 15-30ms

**KV Cache 传输**:
- 1GB KV: ~15-30ms
- 批次越大，影响越显著

### 吞吐量

**无 Offload**:
- LLaMA-70B @ 1× A100: OOM

**CPU Offload**:
- LLaMA-70B @ 1× A100: 5-10 tokens/s
- 吞吐量下降 50-70%

**权衡**:
- 能运行 vs 不能运行
- 慢速推理 vs 完全失败

## 使用建议

### 何时使用 CPU Offload

✓ **GPU 显存不足**: 模型无法完全加载
✓ **长上下文**: KV cache 超出 GPU 容量
✓ **多会话**: 需要支持大量并发
✓ **成本敏感**: CPU 内存更便宜

### 何时避免

✗ **延迟敏感**: 在线服务，SLA 严格
✗ **高吞吐量**: 批量处理任务
✗ **GPU 足够**: 显存充足时 offload 纯粹是开销

### 最佳实践

1. **Profile**: 测量实际瓶颈
2. **混合策略**: 热数据 GPU，冷数据 CPU
3. **异步传输**: Overlap 计算和传输
4. **量化**: 减少传输数据量
5. **监控**: 跟踪 PCIe 利用率

## 未来方向

### 1. 硬件改进
- **CXL**: 更低延迟，缓存一致性
- **PCIe 6.0/7.0**: 更高带宽
- **HBM-PIM**: Processing-In-Memory

### 2. 算法优化
- **智能预测**: 预测访问模式
- **压缩技术**: 更高效的压缩算法
- **混合精度**: 动态调整精度

### 3. 软件框架
- **自动化**: 更智能的 offload 决策
- **透明性**: 对用户完全透明
- **可观测性**: 更好的监控和调试


## 相关概念
- [[gpu-direct-storage]]

- [[gpu-memory-hierarchy]]
- [[flexgen]]
- [[deepspeed]]
