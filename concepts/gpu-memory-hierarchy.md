---
aliases:
- gpu-memory
- memory-hierarchy
tags:
- gpu
- memory
- performance
- hardware
created: '2026-06-09'
---

# gpu-memory-hierarchy

## 定义

GPU Memory Hierarchy（GPU 内存层次）是 GPU 中不同级别存储器的组织结构，从快速但小容量的寄存器到慢速但大容量的全局内存，影响着深度学习模型的性能和内存管理策略。

## 内存层次结构

### 从快到慢的层次

```
速度 ↑     容量 ↓     延迟 ↓
┌─────────────────────────────┐
│  1. 寄存器 (Registers)        │  ~1 cycle, ~KB
├─────────────────────────────┤
│  2. 共享内存 (Shared Memory)  │  ~1-32 cycles, ~KB
├─────────────────────────────┤
│  3. L1 Cache                │  ~32 cycles, ~KB
├─────────────────────────────┤
│  4. L2 Cache                │  ~200 cycles, MB
├─────────────────────────────┤
│  5. HBM/GDDR (Global Memory) │  ~300-600 cycles, GB
├─────────────────────────────┤
│  6. 主机内存 (Host Memory)    │  ~1000s cycles, GB-TB
└─────────────────────────────┘
速度 ↓     容量 ↑     延迟 ↑
```

### 各层详细说明

#### 1. 寄存器 (Registers)
- **容量**: 每个 SM 约 64KB
- **延迟**: ~1 cycle
- **带宽**: 极高
- **用途**: 线程私有数据、中间计算结果
- **限制**: 数量有限，寄存器溢出会降低性能

#### 2. 共享内存 (Shared Memory / SRAM)
- **容量**: 每个 SM 约 48-164KB (架构相关)
- **延迟**: ~1-32 cycles
- **带宽**: ~TB/s 级别
- **用途**: 
  - 线程块内数据共享
  - FlashAttention 的 tiling 缓冲区
  - 手动管理的缓存
- **特点**: 
  - 可编程控制
  - Bank 冲突影响性能

#### 3. L1 Cache
- **容量**: 每个 SM 约 128KB
- **延迟**: ~32 cycles
- **带宽**: TB/s 级别
- **特点**: 
  - 硬件自动管理
  - 与共享内存共享物理存储（可配置分配比例）

#### 4. L2 Cache
- **容量**: 40-80MB (A100), 50MB (H100)
- **延迟**: ~200 cycles
- **带宽**: ~数百 GB/s
- **特点**: 
  - 所有 SM 共享
  - 硬件自动管理
  - 对访问局部性敏感

#### 5. HBM (High Bandwidth Memory)
- **容量**: 40-80GB (A100), 80GB (H100)
- **延迟**: ~300-600 cycles
- **带宽**: 
  - A100: 1.9-2 TB/s
  - H100: 3.35 TB/s
- **特点**: 
  - 主要的模型参数和 KV cache 存储
  - 带宽是推理瓶颈的关键因素

#### 6. 主机内存 (CPU DRAM)
- **容量**: 数百 GB - TB
- **延迟**: ~1000s cycles (含 PCIe 传输)
- **带宽**: 
  - PCIe 4.0 x16: ~64 GB/s
  - PCIe 5.0 x16: ~128 GB/s
- **用途**: 
  - CPU offloading
  - 模型参数存储
  - 大规模 KV cache

## LLM 推理中的内存使用

### Transformer 前向传播的内存访问

#### Attention 计算
```python
# Q, K, V 从 HBM 加载
Q = load_from_HBM(batch, seq_len, hidden_dim)  # ~GB
K = load_from_HBM(batch, seq_len, hidden_dim)
V = load_from_HBM(batch, seq_len, hidden_dim)

# 在 SRAM/L1 中进行 tiling 计算（FlashAttention）
for tile in tiles:
    Q_tile = load_to_SRAM(Q[tile])  # ~KB
    K_tile = load_to_SRAM(K[tile])
    # 计算 attention scores
    # 输出写回 HBM
```

#### KV Cache 存储
- **位置**: 主要在 HBM
- **大小**: batch_size × seq_len × num_layers × 2 × hidden_dim
- **瓶颈**: HBM 容量和带宽

### 内存占用估算

**模型参数**:
- LLaMA-70B (FP16): ~140GB
- LLaMA-7B (FP16): ~14GB

**KV Cache (FP16)**:
```
单层: 2 × batch × seq_len × hidden_dim × 2 bytes
总计: 上述 × num_layers

示例 (LLaMA-70B, batch=1, seq=2048):
2 × 1 × 2048 × 8192 × 2 × 80 layers
= ~5GB per request
```

**激活值**:
- 中间计算结果
- 通常 < 1GB

## 内存优化策略

### 1. 分层存储
- **HBM**: 热点参数、当前 batch KV cache
- **Host Memory**: 冷参数、历史 KV cache
- **SSD**: 长期存储、模型检查点

### 2. 重计算 (Recomputation)
- **策略**: 不存储中间激活，需要时重新计算
- **权衡**: 内存换计算
- **应用**: FlashAttention 反向传播

### 3. 量化
- **FP16 → INT8**: 2× 内存节省
- **FP16 → INT4**: 4× 内存节省
- **权衡**: 精度略微下降

### 4. Offloading
- **CPU Offload**: 参数或 KV cache 到主机内存
- **SSD Offload**: 更大规模的 offloading
- **权衡**: 延迟增加

## 性能考量

### 带宽限制

**计算强度 (Arithmetic Intensity)**:
```
AI = FLOPs / Bytes_Transferred

高 AI (> 100): 计算瓶颈
低 AI (< 10): 内存带宽瓶颈
```

**LLM 推理通常是内存瓶颈**:
- Decode 阶段: AI ~1-5 (带宽瓶颈)
- Prefill 阶段: AI ~50-100 (计算接近)

### 延迟分析

**HBM 访问延迟**:
- 单次访问: ~300-600 cycles (~300-600ns @ 1GHz)
- 连续访问: 带宽限制 (~2TB/s)

**PCIe 传输延迟**:
- 小数据 (<1MB): 延迟主导 (~10-50μs)
- 大数据 (>100MB): 带宽主导 (~GB/s)

### 优化目标

1. **最小化 HBM 访问**: Kernel fusion, tiling
2. **最大化数据重用**: Shared memory, L1/L2 cache
3. **隐藏延迟**: Async copies, 计算与传输重叠

## 硬件架构演进

### NVIDIA GPU 代际对比

| 架构 | SM数 | HBM容量 | HBM带宽 | L2 Cache |
|------|-----|---------|---------|----------|
| V100 | 80 | 32GB | 900 GB/s | 6MB |
| A100 | 108 | 80GB | 2.0 TB/s | 40MB |
| H100 | 132 | 80GB | 3.35 TB/s | 50MB |

**趋势**:
- HBM 带宽持续增长
- L2 Cache 显著增大
- SM 数量增加

### 新兴技术

#### HBM3/HBM3E
- **带宽**: 5+ TB/s
- **容量**: 128GB+
- **能效**: 更低功耗

#### CXL Memory
- **扩展容量**: TB 级
- **共享内存**: CPU-GPU 统一地址空间
- **延迟**: 高于 HBM，低于 PCIe

## 编程模型考量

### CUDA 内存操作

```cuda
// 全局内存访问
__global__ void kernel(float* data) {
    int idx = threadIdx.x;
    float val = data[idx];  // HBM 访问
}

// 共享内存使用
__global__ void kernel_optimized(float* data) {
    __shared__ float shared_data[256];  // SRAM
    int idx = threadIdx.x;
    
    // 协作加载到共享内存
    shared_data[idx] = data[idx];
    __syncthreads();
    
    // 从共享内存读取（快）
    float val = shared_data[idx];
}
```

### FlashAttention 的内存策略
- **Tiling**: 将 Q, K, V 分块加载到 SRAM
- **Recomputation**: 反向传播时重计算 attention 矩阵
- **IO-aware**: 最小化 HBM ↔ SRAM 数据传输

## 监控和诊断

### 关键指标
- **Memory Bandwidth Utilization**: 实际带宽 / 理论峰值
- **Cache Hit Rate**: L1/L2 缓存命中率
- **Memory Copy Time**: 数据传输时间占比

### 工具
- **NVIDIA Nsight Compute**: Kernel 级别内存分析
- **NVIDIA Nsight Systems**: 系统级别性能分析
- **PyTorch Profiler**: 高层 API 分析


## 相关概念
- [[cpu-offload]]

- [[kv-cache]]
- [[flash-attention]]
- [[hbm]]
