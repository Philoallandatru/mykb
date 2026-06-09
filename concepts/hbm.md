---
aliases:
- high-bandwidth-memory
- hbm2
- hbm3
tags:
- hardware
- memory
- gpu
- performance
created: '2026-06-10'
---

# hbm

## 定义

HBM (High Bandwidth Memory) 是一种高性能 3D 堆叠内存技术，为 GPU 和加速器提供极高的内存带宽，是现代 AI 芯片的核心组件。

## 技术架构

### 3D 堆叠结构
```
垂直堆叠:
┌─────────────┐
│  DRAM Die 8 │  
├─────────────┤
│  DRAM Die 7 │
├─────────────┤
│     ...     │
├─────────────┤
│  DRAM Die 1 │
├─────────────┤
│ Logic Base  │ ← 包含控制逻辑
└─────────────┘
     ↓ TSV (Through-Silicon Via)
┌─────────────┐
│   Interposer│ ← 连接 GPU
└─────────────┘
```

**TSV (硅通孔)**:
- 垂直穿过硅片的导线
- 连接堆叠的 DRAM 层
- 实现高密度互连

### 与传统内存对比

| 特性 | HBM | GDDR6 | DDR5 |
|------|-----|-------|------|
| 带宽 | 2-3.35 TB/s | 768 GB/s | 100 GB/s |
| 总线宽度 | 1024-bit | 384-bit | 64-bit |
| 功耗效率 | 优秀 | 中等 | 一般 |
| 容量 | 40-80 GB | 24 GB | 数百GB |
| 延迟 | 中 | 低 | 高 |
| 成本 | 高 | 中 | 低 |

## HBM 代际演进

### HBM (第一代, 2013)
- 带宽: 128 GB/s per stack
- 容量: 1-4 GB per stack
- 速率: 1 Gbps

### HBM2 (2016)
- 带宽: 256 GB/s per stack
- 容量: 4-8 GB per stack
- 速率: 2 Gbps
- **应用**: NVIDIA V100

### HBM2E (2018)
- 带宽: 460 GB/s per stack
- 容量: 16 GB per stack
- 速率: 3.6 Gbps
- **应用**: NVIDIA A100 (1.9-2 TB/s 总带宽)

### HBM3 (2022)
- 带宽: 600+ GB/s per stack
- 容量: 24 GB per stack
- 速率: 6 Gbps
- **应用**: NVIDIA H100 (3.35 TB/s 总带宽)

### HBM3E (2024)
- 带宽: 1 TB/s per stack
- 容量: 32 GB per stack
- 速率: 9.6 Gbps
- **应用**: NVIDIA H200, AMD MI300

## 性能特征

### 带宽优势
```
实际应用 (A100, 80GB):
- 理论峰值: 2.0 TB/s
- 实际可达: 1.5-1.8 TB/s (75-90%)
- 相比 GDDR6: 2.6× 带宽

影响:
- LLM 推理: 内存带宽瓶颈
- 训练: 梯度传输
- Decode 阶段: 几乎完全受限于 HBM 带宽
```

### 功耗效率
```
能效比:
- HBM2E: ~2 pJ/bit
- GDDR6: ~5 pJ/bit
- DDR5: ~10 pJ/bit

结果: HBM 功耗更低（相同带宽下）
```

### 延迟特性
```
访问延迟:
- HBM: ~300-600 cycles (@1 GHz = 300-600 ns)
- GDDR6: ~200-400 cycles
- SRAM (L1/L2): ~1-32 cycles

权衡: 高带宽 vs 中等延迟
```

## LLM 场景应用

### 推理瓶颈
```python
# Decode 阶段计算强度
Compute: O(batch × hidden_dim²)
Memory: O(batch × seq_len × hidden_dim)

当 batch 小时:
- Compute 时间 < Memory 时间
- HBM 带宽成为瓶颈

实测 (A100, LLaMA-70B):
- GPU 利用率: 30-40%
- 瓶颈: HBM 带宽 (1.9 TB/s)
```

### KV Cache 存储
```
LLaMA-70B:
- 单个 token: ~560 KB (FP16)
- 2048 上下文: ~1.1 GB
- Batch 32: ~35 GB

HBM 容量限制:
- A100 (80GB): Batch ~64
- H100 (80GB): 相同容量，但带宽更高
```

### 优化策略
```
降低 HBM 压力:
1. Kernel Fusion - 减少内存往返
2. FlashAttention - SRAM tiling
3. Quantization - 降低数据量
4. Offloading - 冷数据到 CPU/SSD
```

## 硬件集成

### GPU 中的 HBM
```
NVIDIA A100:
- 5 个 HBM2E stacks
- 每个 stack: 16 GB
- 总容量: 80 GB
- 总带宽: 2.0 TB/s

NVIDIA H100:
- 5 个 HBM3 stacks
- 每个 stack: 16 GB
- 总容量: 80 GB
- 总带宽: 3.35 TB/s (+67%)
```

### Interposer 技术
```
作用:
- 连接 GPU die 和 HBM stacks
- 提供高密度布线
- 成本: 增加制造复杂度

替代: CoWoS (Chip-on-Wafer-on-Substrate)
```

## 成本和供应

### 制造挑战
- **良率**: 3D 堆叠复杂，良率低
- **成本**: 比 GDDR6 贵 2-3×
- **产能**: 供应商有限（SK hynix, Samsung, Micron）

### 供应链
```
主要供应商:
- SK hynix: 市场领导者 (~50%)
- Samsung: 第二大供应商
- Micron: 新进入者

瓶颈:
- 产能受限
- 高端 AI 芯片需求激增
- 2023-2024 供应紧张
```

## 未来发展

### HBM4 (预计 2026)
- 带宽: 1.5+ TB/s per stack
- 容量: 48+ GB per stack
- ECC 增强
- 更低功耗

### 新技术
**Processing-In-Memory (PIM)**:
- 在 HBM 内部进行计算
- 减少数据移动
- 适合特定操作（矩阵乘法）

**HBM-PNM (Processing Near Memory)**:
- 逻辑层增强
- 更复杂的计算能力

## 竞争技术

### GDDR6X
- **优势**: 成本低，成熟技术
- **劣势**: 带宽和能效不如 HBM
- **应用**: 消费级 GPU (RTX 40 系列)

### CXL Memory
- **优势**: 扩展容量
- **劣势**: 带宽和延迟不如 HBM
- **应用**: 扩展内存池，补充 HBM

### On-Package Memory
- **概念**: 内存更靠近计算单元
- **优势**: 更低延迟
- **挑战**: 容量限制

## 性能调优

### 最大化带宽利用
```python
# 1. 合并访问
# 坏: 多次小访问
for i in range(N):
    data[i] = load_from_hbm(addr + i)

# 好: 批量访问
data = load_from_hbm_batch(addr, N)

# 2. 减少往返
# 使用 kernel fusion
fused_kernel(input) # HBM → Compute → HBM (一次)

# 3. Prefetch
async_load_from_hbm(next_data)
compute(current_data)
```

### Profile HBM 利用率
```bash
# NVIDIA Nsight Compute
ncu --metrics dram__throughput.avg.pct_of_peak \
    ./inference

# 目标: 80-90% 利用率
# <50%: 计算瓶颈或未优化
# >90%: HBM 带宽瓶颈
```

## 与其他概念的关系

- **GPU Memory Hierarchy**: HBM 是最大的片上内存层
- **FlashAttention**: 利用 SRAM 减少 HBM 访问
- **KV Cache**: 主要存储在 HBM
- **CPU Offload**: HBM 不足时的解决方案
- **Quantization**: 降低 HBM 带宽需求


## 相关概念

- [[gpu-memory-hierarchy]]
- [[kv-cache]]
- [[flash-attention]]
