# MLPerf KV Cache Benchmark v3.0
## Technical Specification and Implementation Guide

**Date:** January 27, 2026  
**Author:** Hazem Awadallah <hazem_awadallah@kingston.com>, Kingston Digital  
**Note:** AI tooling was used to draft code under architectural direction.

---

## Executive Summary

### The Problem

Large Language Models generate text one token at a time, maintaining context through a data structure called the **KV Cache** that stores attention state. This cache eliminates redundant computation but grows linearly with sequence length; a single 8K-token conversation with a 70B model consumes **2.5 GB of memory**.

At scale, this quickly exhausts GPU VRAM, forcing systems to offload data to slower tiers: CPU RAM or NVMe storage. The challenge: **quantifying the performance trade-offs** of multi-tier storage architectures.

### The Solution

This benchmark simulates realistic LLM inference workloads to answer critical capacity planning questions:

- **Tier Performance:** How much faster is GPU vs. CPU vs. NVMe?
- **Capacity Planning:** How many concurrent users can my storage sustain at a given throughput?
- **Hardware Validation:** Which NVMe drive delivers optimal throughput for LLM inference?
- **Bottleneck Identification:** Where is the storage bottleneck in my system?

> **Scope note; no tier promotion:** The benchmark uses a one-way waterfall: data flows from GPU → CPU → NVMe but is never promoted back to a faster tier on read. This is intentional for isolating storage performance; it ensures NVMe is stressed on every read.

> **Terminology; "NVMe" as shorthand:** Throughout this document, "NVMe" refers to the benchmark's third storage tier (the `--cache-dir` filesystem path). The benchmark is not NVMe-specific; it writes `.npy` files via standard POSIX I/O and works with any block device or filesystem: SATA SSD, HDD, RAM disk, NFS, EBS, etc.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Workload Generator  →  Multi-Tier Cache  →  Storage Tiers │
│  (Requests/Users)       (Waterfall LRU)      (GPU/CPU/NVMe)│
│                                                             │
│  ↓                      ↓                     ↓             │
│  Telemetry             Priority Queue        Device I/O    │
│  (4 Latency Layers)    (QoS Classes)         (Hardware)    │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Waterfall LRU:** Hot data stays in fast tiers; cold data cascades to storage
- **Hardware Validation:** Bypasses OS caching (`posix_fadvise`) for true device measurement
- **Autoscaling:** Automatically discovers maximum sustainable load
- **Production Realism:** Simulates GPU compute, RAG workloads, prefix caching, multi-turn conversations

---

## Quick Start: Four Essential Tests

All examples use `llama3.1-8b` and assume `/mnt/nvme` as the cache directory. Use `--seed 42` for reproducibility.

### Test 1: Storage Baseline (Device Isolation)

**Purpose:** Measure raw NVMe performance by forcing 100% storage utilization.

```bash
python3 kv-cache.py \
    --config config.yaml \
    --model llama3.1-8b \
    --num-users 200 \
    --duration 300 \
    --gpu-mem-gb 0 \
    --cpu-mem-gb 0 \
    --max-concurrent-allocs 16 \
    --generation-mode none \
    --cache-dir /mnt/nvme \
    --seed 42 \
    --output results_storage_baseline.json
```

**Key Metrics:**
- `decode_bytes_read_gb` – I/O volume (2.6× differentiation fast/slow drives)
- `avg_throughput_tokens_per_sec` – Wall-clock throughput (2.4× differentiation)
- `nvme_read_device_p95_ms` – Hardware read latency (P95)
- `nvme_write_device_p95_ms` – Hardware write latency (P95)

### Test 2: Production Simulation (Three-Tier)

**Purpose:** Model realistic workload with GPU/CPU/NVMe hierarchy and simulated inference compute.

```bash
python3 kv-cache.py \
    --config config.yaml \
    --model llama3.1-8b \
    --num-users 100 \
    --duration 300 \
    --gpu-mem-gb 16 \
    --cpu-mem-gb 32 \
    --generation-mode realistic \
    --cache-dir /mnt/nvme \
    --seed 42 \
    --output results_production.json
```

**Key Metrics:**
- `end_to_end_latency_p95_ms` – User-facing latency
- `cache_hit_rate` – % served from fast tiers
- Tier distribution – `gpu_entries`, `cpu_entries`, `nvme_entries`

### Test 3: Capacity Planning (QoS Autoscaler)

**Purpose:** Discover maximum users while maintaining latency SLAs.

```bash
python3 kv-cache.py \
    --config config.yaml \
    --model llama3.1-8b \
    --num-users 20 \
    --duration 300 \
    --gpu-mem-gb 16 \
    --cpu-mem-gb 32 \
    --enable-autoscaling \
    --autoscaler-mode qos \
    --generation-mode realistic \
    --cache-dir /mnt/nvme \
    --seed 42 \
    --output results_qos.json
```

**Key Metrics:**
- `autoscaling_stats[last].users` – Final stabilized count
- `qos_stats` – Per-class latency vs. SLA

### Test 4: Peak Throughput (Capacity Autoscaler)

**Purpose:** Find absolute maximum I/O throughput (ignores latency).

```bash
python3 kv-cache.py \
    --config config.yaml \
    --model llama3.1-70b-instruct \
    --num-users 10 \
    --duration 180 \
    --gpu-mem-gb 0 \
    --cpu-mem-gb 32 \
    --enable-autoscaling \
    --autoscaler-mode capacity \
    --generation-mode none \
    --cache-dir /mnt/nvme \
    --seed 42 \
    --output results_capacity.json
```

**Key Metrics:**
- `peak_throughput` – Max tokens/sec
- `reason: "Peak capacity found"` in `autoscaling_stats`

---

## 核心特性

### 1. 三层瀑布缓存架构（Waterfall LRU）

```
GPU VRAM (热数据)
  ↓ LRU eviction
CPU RAM (温数据)
  ↓ LRU eviction
NVMe SSD (冷数据)
  ↓ LRU deletion
```

**特点**：
- 新数据优先写入GPU
- GPU满时LRU entry级联到CPU
- CPU满时LRU entry级联到NVMe
- NVMe满时LRU entry永久删除
- **无数据回流（no promotion）** - 数据只向下流动，从不回流到快速层

### 2. 四层延迟遥测（Four-Layer Latency Hierarchy）

```
L1: End-to-End Latency (用户感知总延迟)
  └─ L2: Per-Request Storage Latency (单请求I/O总时间)
      └─ L3: Per-Tier Total Latency (单次文件I/O时间)
          └─ L4: Host vs Device Breakdown (CPU vs 磁盘分解)
```

**L4分解重要说明**：
- **Write Host**: `np.save()` 序列化时间
- **Write Device**: `fsync()` 刷盘时间
- **Read Device**: `np.load()` 文件读取+反序列化
- **Read Host**: `posix_fadvise()` + array copy

**⚠️ "Device"不是纯NVMe延迟** - 包含OS/文件系统开销。要分离纯NVMe延迟，需结合`iostat`。

### 3. KV Cache大小计算

**MHA/GQA模型**：
```
Bytes per Token = num_layers × 2 × kv_heads × head_dim × bytes_per_dtype
```

**MLA模型（DeepSeek-V3）**：
```
Bytes per Token = num_layers × (kv_lora_rank + qk_rope_head_dim) × bytes_per_dtype
```

| Model | Architecture | MB/Token | 8K Context |
|-------|--------------|----------|------------|
| `tiny-1b` | GQA | 0.023 | 192 MB |
| `mistral-7b` | GQA | 0.125 | 1,024 MB |
| `llama2-7b` | **MHA** | **0.500** | **4,096 MB** |
| `llama3.1-8b` | GQA | 0.125 | 1,024 MB |
| `llama3.1-70b-instruct` | GQA | 0.313 | 2,560 MB |
| `deepseek-v3` | **MLA** | 0.067 | 549 MB |

**为什么llama2-7b这么大**？它使用MHA（32个KV heads），而llama3.1-8b使用GQA（8个KV heads），4×差异。

### 4. 内存需求

**公式**：
```
Minimum RAM = cpu_mem_gb + peak_in_flight_RAM + 4 GB overhead
Peak In-Flight RAM = max_concurrent_allocs × avg_context × bytes_per_token
```

**关键参数**：
- `--max-concurrent-allocs 0` (unlimited): **危险** - 可能OOM
- `--max-concurrent-allocs 16`: **推荐** - 限制并发分配

**内存推荐**：

| System RAM | `--max-concurrent-allocs` | Safe Models |
|------------|---------------------------|-------------|
| 32 GB | 4 | `tiny-1b`, `deepseek-v3` |
| 64 GB | 8 | `mistral-7b`, `llama3.1-8b` |
| 128 GB | 16 | 所有GQA/MoE/MLA模型 |
| 256 GB | 16–32 | 所有模型（有界并发） |
| 512 GB+ | 32–64 | 所有模型包括`llama2-7b` (MHA) |

### 5. 用户配置文件（User Profiles）

基于真实生产工作负载研究：

| Profile | Context Range | Generation Range | 依据 |
|---------|---------------|------------------|------|
| **chatbot** | 512-4096 | 50-200 | 通用对话，非编程类别保持低容量[OpenRouter研究] |
| **coding** | 4096-25000 | 100-500 | 编程是上下文长度的主要驱动，平均>20K输入[OpenRouter研究] |
| **document** | 4096-16384 | 200-800 | 长上下文文档分析，介于chatbot和coding之间 |

**研究来源**：
- OpenRouter "State of AI: An Empirical 100T Token Study" (arXiv:2601.10088)
- BurstGPT (arXiv:2401.17644) - 10.31M traces from Azure OpenAI GPT

### 6. Generation Mode（模拟GPU反压）

| Mode | Behavior | Use Case |
|------|----------|----------|
| `none` | 无sleep（0 ms/token） | 纯存储benchmark |
| `fast` | 最小sleep（2 ms/token） | 轻负载压力测试 |
| `realistic` | 按token生成sleep（30 ms/token） | 生产模拟 |

**Realistic模式计算**：
```python
# 基于NVIDIA A100推理速度（~33 tok/s）
sleep_time = generate_tokens * 0.030  # 每token 30ms
```

### 7. QoS Classes（质量服务等级）

| QoS Level | Use Case | Target P95 | Target P99 | Priority |
|-----------|----------|------------|------------|----------|
| **INTERACTIVE** | 实时聊天机器人 | 50 ms | 100 ms | 3 (最高) |
| **RESPONSIVE** | 近实时 | 100 ms | 200 ms | 2 |
| **BATCH** | 离线作业 | 1,000 ms | 5,000 ms | 1 (最低) |

**默认分布**：15% Interactive, 35% Responsive, 50% Batch

### 8. Prefix Caching（系统提示优化）

**三个常见提示**：
```python
COMMON_SYSTEM_PROMPTS = [
    "You are a helpful assistant.",
    "You are an AI assistant helping with coding tasks.",
    "You are a professional writing assistant.",
]
```

**Cache Key**: `kv_system_{sha256_hash[:16]}`

**好处**：避免重复存储相同的系统提示，节省存储和计算。

### 9. RAG Workflow（检索增强生成）

**三个阶段**：
1. **Ingestion**（离线） – 分割文档 → 计算KV cache → 存储
2. **Retrieval**（每次查询） – 向量相似度搜索 → 返回top_k chunks
3. **Inference**（每次查询） – 加载chunk KV caches → 拼接 → 生成

**读放大**：

| Metric | Standard Chat | RAG Query |
|--------|---------------|-----------|
| Context at start | ~1 KB | **500 MB - 2 GB** |
| Reads before first token | 1 | **10-50** |
| Storage pressure | Gradual | **Instant burst** |

**启用**：`--enable-rag --rag-top-k 10`

### 10. Autoscaling Modes（自动扩展模式）

#### QoS Mode（生产容量规划）

**目标**：在维持延迟SLA的同时找到最大用户数

**逻辑**：
```
收集KPI（每5s的P95延迟）
  ↓
计算饱和度（0.0 - 1.0）
  ↓
与目标比较（默认0.8）
  ↓
调整负载：
  - 饱和度 < 0.7 → 增加用户（+10-20%）
  - 0.7 ≤ 饱和度 ≤ 0.9 → 保持稳定
  - 饱和度 > 0.9 → 减少用户 + 冷却（30s）
```

#### Capacity Mode（硬件benchmark）

**目标**：找到绝对峰值吞吐量（忽略延迟）

**逻辑**：
```
Ramp-up Phase: 吞吐量快速增长时用户数翻倍
  ↓
Fine-tune Phase: 增长放缓时1.5×扩展
  ↓
终止: 吞吐量从上一阶段下降时
```

---

## Validation Results（验证结果）

### 测试环境

| Component | Specification |
|-----------|---------------|
| **Server** | Supermicro SYS-621H-TN12R |
| **CPU** | 2× Intel Xeon Silver 4510 (48T total) |
| **RAM** | 256 GB DDR5-4800 ECC |
| **GPU** | NVIDIA H100 NVL (94 GB HBM3) |
| **NVMe** | 7.0 TB enterprise SSD (~14 GB/s) |
| **OS** | Ubuntu 22.04, Linux 6.5.0 |

### 存储层差异化

**配置**：Mistral-7B, 500 prompts (ShareGPT), 50 concurrent users, 3 trials each

| Tier | Storage Throughput | Speedup vs NVMe |
|------|-------------------|-----------------|
| **GPU Only** | 1,691 ± 154 tok/s | **6.4×** |
| **GPU + CPU** | 1,546 ± 257 tok/s | **5.9×** |
| **GPU + CPU + NVMe** | 1,175 ± 178 tok/s | **4.4×** |
| **NVMe Only** | 263 ± 2 tok/s | 1.0× (baseline) |

**结论**：GPU相比NVMe提供6.4×性能提升。

### 快速vs慢速系统对比

**Systems**:
- **Fast**: Bare metal, 7.0 TB NVMe (14 GB/s theoretical)
- **Slow**: VMware ESXi 8.0.3, VMFS6 volume (3 GB/s theoretical)

**Global Results (220 matched configurations)**:

| Metric | Fast | Slow | Ratio |
|--------|------|------|-------|
| Storage Throughput | 88.47 tok/s | 41.56 tok/s | **2.13×** |
| Wall-Clock Throughput | 610.36 tok/s | 290.02 tok/s | **2.10×** |
| Storage Latency P95 | 36,504 ms | 45,091 ms | **1.24×** |

**关键发现**：在`cpu_mem=0GB`时，使用**Decode Bytes Read**或**Wall-Clock Throughput**进行区分，不要使用Storage Throughput（仅1.12×，因为两个系统都是100% I/O bound）。

### iostat验证

**不同内存层的最大存储利用率**：

| `cpu_mem` | Avg Read MB/s | Avg Total MB/s | Util% |
|-----------|---------------|----------------|-------|
| **0 GB** | **6,825** | **7,680** | **211%** |
| 4 GB | 1,714 | 2,741 | 51% |
| 8 GB | 628 | 1,719 | 38% |
| 16 GB | 47 | 1,188 | 38% |

**峰值性能**：`cpu_mem=0GB`配合`llama3.1-8b`在200 users时实现**10.9 GB/s**（78%理论极限）。

---

## MLPerf v3.0提交指南

### 推荐配置

#### Option 1: Maximum Storage Stress (cpu_mem=0GB)

**使用场景**：测量I/O容量差异化和硬件压力。

**主要指标**：
- `decode_bytes_read_gb` (2.62× differentiation, 100% win rate)
- `avg_throughput_tokens_per_sec` (2.43× differentiation, 100% win rate)
- `nvme_read_device_p95_ms`, `nvme_write_device_p95_ms`

⚠️ **不要使用** `storage_throughput` at `cpu_mem=0GB`（仅1.12× differentiation）。

```bash
for trial in {1..5}; do
    python3 kv-cache.py \
        --config config.yaml \
        --model llama3.1-8b \
        --num-users 200 \
        --duration 300 \
        --gpu-mem-gb 0 \
        --cpu-mem-gb 0 \
        --max-concurrent-allocs 16 \
        --generation-mode none \
        --cache-dir /mnt/nvme \
        --seed 42 \
        --output mlperf_stress_8b_trial${trial}.json
done
```

#### Option 2: Storage Throughput Focus (cpu_mem=4GB)

**使用场景**：Storage Throughput是主要指标。

**主要指标**：
- `storage_throughput_tokens_per_sec` (2.23× differentiation, 97.2% win rate)
- `decode_bytes_read_gb`
- `nvme_read_device_p95_ms`, `nvme_write_device_p95_ms`

```bash
for trial in {1..5}; do
    python3 kv-cache.py \
        --config config.yaml \
        --model llama3.1-8b \
        --num-users 100 \
        --duration 300 \
        --gpu-mem-gb 0 \
        --cpu-mem-gb 4 \
        --generation-mode none \
        --cache-dir /mnt/nvme \
        --seed 42 \
        --output mlperf_throughput_8b_trial${trial}.json
done
```

#### Option 3: Large Model (70B)

**使用场景**：最大单请求存储压力（70B的KV cache/token约为2.5×）。

```bash
for trial in {1..3}; do
    python3 kv-cache.py \
        --config config.yaml \
        --model llama3.1-70b-instruct \
        --num-users 70 \
        --duration 300 \
        --gpu-mem-gb 0 \
        --cpu-mem-gb 0 \
        --max-concurrent-allocs 4 \
        --generation-mode none \
        --cache-dir /mnt/nvme \
        --seed 42 \
        --output mlperf_stress_70b_trial${trial}.json
done
```

### 关键参数

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `--seed 42` | **Required** | 可重复性 |
| `--gpu-mem-gb 0` | **Required** | 隔离存储 |
| `--generation-mode` | `none` | 纯存储benchmark |
| `--cpu-mem-gb` | 0 or 4 | 0用于最大压力；4用于吞吐量指标 |
| `--max-concurrent-allocs` | 0, 4, or 16 | 控制RAM使用 |
| `--duration` | 300-600 | 稳态要求 |

### Trial要求

**高方差观察到（CV 50-125%）需要多次trial**：

| User Count | Variance (CV) | Min Trials |
|------------|---------------|------------|
| 10 users | ~52% | 3 |
| 50-100 users | ~115-125% | 3-5 |
| 200 users | ~110-120% | 3-5 |

**报告中位数，而非平均值。**

---

## 高级特性

### ShareGPT Dataset Replay

**来源**：[ShareGPT](https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered) - 90K+真实人类-ChatGPT对话

**为什么选择ShareGPT**：
- 真实对话模式
- 多样化用例（编程、写作、Q&A、头脑风暴）
- 真实token分布（平均~133输入tokens，~150输出tokens）

**使用**：
```bash
kv-cache \
    --dataset-path /path/to/ShareGPT_V3_filtered.json \
    --max-conversations 1000 \
    --replay-cycles 3 \
    --model llama3.1-8b \
    --num-users 50 \
    --duration 300 \
    --gpu-mem-gb 0 --cpu-mem-gb 0 \
    --cache-dir /mnt/nvme
```

### BurstGPT Trace Replay

**来源**：Wang et al., "BurstGPT" (arXiv:2401.17644, KDD '25)

**特点**：
- **10.31M生产API调用** - Azure OpenAI 121天trace
- Zipf分布的请求长度
- 双峰响应模式
- 真实token分布（平均621请求tokens，126响应tokens）

**使用**：
```bash
kv-cache \
    --config config.yaml \
    --model llama3.1-8b \
    --use-burst-trace \
    --burst-trace-path BurstGPT/data/ \
    --trace-speedup 0 \
    --replay-cycles 5 \
    --num-users 50 \
    --duration 300 \
    --gpu-mem-gb 0 --cpu-mem-gb 0 \
    --cache-dir /mnt/nvme \
    --output results_burst.json
```

**Speedup示例**：

| `--trace-speedup` | Behavior | Use Case |
|-------------------|----------|----------|
| `1.0` | 实时（原始timestamps） | 验证时间模式 |
| `10.0` | 10×加速 | 快速压力测试 |
| `0` | 无延迟（饱和） | **最大存储压力** |

### Disaggregated Inference Modes（解耦推理模式）

现代推理系统（vLLM, TensorRT-LLM, Mooncake）经常将**prefill**和**decode**分离到不同的节点池。

| Mode | CLI Flag | I/O Pattern | Simulates |
|------|----------|-------------|-----------|
| Standard | *(none)* | Mixed R/W | Colocated prefill+decode |
| Prefill-only | `--prefill-only` | **Write-heavy** | Disaggregated prefill node |
| Decode-only | `--decode-only` | **Read-heavy** | Disaggregated decode node |

**示例**：
```bash
# Test prefill node (write-heavy)
python3 kv-cache.py --model llama3.1-70b-instruct --prefill-only \
    --gpu-mem-gb 0 --cpu-mem-gb 0 \
    --num-users 100 --duration 300 --cache-dir /mnt/nvme

# Test decode node (read-heavy)
python3 kv-cache.py --model llama3.1-70b-instruct --decode-only \
    --gpu-mem-gb 0 --cpu-mem-gb 0 \
    --num-users 100 --duration 300 --cache-dir /mnt/nvme
```

### Block-Layer Latency Tracing & fio Workload Distiller

**功能**：集成的块层追踪能力，分解Linux I/O栈每一层的存储I/O（从应用VFS到NVMe控制器D2C）。

**启用**：
```bash
kv-cache --config config.yaml --model llama3.1-8b \
    --num-users 10 --duration 30 \
    --gpu-mem-gb 0 --cpu-mem-gb 0 \
    --enable-latency-tracing \
    --xlsx-output results_traced.xlsx
```

**捕获的直方图**：
- D2C read/write（设备）- 每个NVMe命令完成时间
- Q2D read/write（I/O调度器）- 调度队列等待时间
- VFS read/write（应用层）- 完整syscall时间
- fsync（设备）- 缓冲写入后的实际设备刷新延迟
- bssplit read/write（块大小）- 内核层的I/O大小分布
- Queue depth read/write（并发度）- dispatch时的瞬时in-flight I/O计数
- LBA heatmap read/write（空间）- I/O落在设备的哪里

**fio Workload Distiller**：

当启用追踪时，benchmark自动生成一个独立的fio .ini文件，重现观察到的I/O模式。可以针对任何推理引擎使用：

```bash
# Trace vLLM and generate fio workload
sudo ./utils/storage_latency_stack.sh vllm --fio

# Trace llm-d
sudo ./utils/storage_latency_stack.sh llm-d --fio
```

---

## 相关概念

- [[kv-cache]] - KV cache核心概念
- [[mlcommons-storage]] - MLCommons Storage benchmark
- [[lmcache]] - LMCache KV cache middleware
- [[vllm]] - vLLM推理框架
- [[ai-ssd]] - AI SSD核心定义
- [[ai-ssd-benchmark-design]] - AI SSD benchmark方法论

---

**标签**: #benchmark #mlperf #kv-cache #storage #nvme #validation #waterfall-lru
