---
type: raw
source: technical-analysis
date: 2026-06-04
status: pending
tags:
  - offloading
  - ai-ssd
  - kv-cache
  - systems
  - architecture
  - llm
  - research
---

# LLM/AI系统中的Offloading技术演进（2026年6月）

## 📋 概述

这是一份关于截至2026年6月LLM/AI系统中offloading技术的全面分析，涵盖从GPU显存扩展到分布式KV缓存、近存储计算等9个主要研究方向。

## 🔄 Offloading的演进

### Offloading 1.0
- **目标**: 模型能跑起来
- **方法**: 权重/optimizer/activation从GPU → CPU/NVMe

### Offloading 2.0  
- **目标**: 长上下文和高并发
- **方法**: KV cache从GPU → CPU/SSD

### Offloading 3.0
- **目标**: 减少重复prefill，降低TTFT和成本
- **方法**: KV cache共享 + 分布式 + cache-aware routing

### Offloading 4.0
- **目标**: 不再搬完整KV，而是在数据附近计算/筛选
- **方法**: 近存储计算 / CXL-PNM / SmartSSD

### Offloading 5.0
- **目标**: 在准确率、延迟、成本、能耗之间动态权衡
- **方法**: 压缩 + 选择 + offload + recompute联合优化

## 🎯 Offloading对象的扩展

**传统对象**:
- Model weights
- Optimizer states
- Activations

**新增重点**:
- KV cache ⭐
- Attention compute
- MoE experts
- Prefill cache
- RAG embedding/index
- Cross-node cache
- Agent long-term context memory

## 📊 9个主要研究方向

### 1️⃣ KV Cache分层Offloading

**内存层次**:
```
GPU HBM
  ↓
CPU DRAM
  ↓
CXL Memory
  ↓
Local SSD
  ↓
Remote SSD / Distributed Storage
```

**代表系统**:
- **LMCache** - 开源KV cache层，支持vLLM/SGLang
- **NVIDIA Dynamo** - 企业级解决方案
- **llm-d** - 分布式KV cache
- **KServe + vLLM + LMCache** - 生产级集成

**关键特点**:
- 跨查询和跨engine共享KV cache
- 支持cache offloading和disaggregation
- 降低prefill delay和GPU utilization
- 适合多轮QA和RAG场景

**对SSD的要求**:
- 64K~256K random read p99性能
- Mixed read/write下的read QoS
- 低QD/中QD延迟
- GPU Direct Storage路径
- 多进程/多租户cache访问隔离

### 2️⃣ GPU-centric SSD KV Cache

**代表工作**: [[tutti|Tutti]]

**核心问题**: 
传统LMCache-SSD/GDS方案的CPU提交开销:
- CPU submission overhead
- 小随机I/O
- GPU等数据
- SSD bandwidth无法吃满
- GPU bubble time增加

**Tutti的创新**:
- GPU-centric的KV cache object store
- I/O queue和I/O kernel靠近GPU
- GPU批量发起和调度SSD I/O
- 消除CPU干预的关键路径

**对固件的启发**:
- NVMe SGL/PRP对大批量中等大小对象的效率
- 多queue并发调度
- GPU Direct Storage读路径稳定性
- 小对象随机读聚合
- Read latency tail control
- 避免GC阻塞GPU等待路径

### 3️⃣ Near-storage / In-storage Compute

**核心思想**: 不搬完整KV，在存储侧先处理

**工作流程**:
```
传统: SSD → PCIe → GPU → attention

新方向: SSD/SmartSSD内部先筛选/部分attention
         ↓
       只把结果或少量token搬给GPU
```

**代表工作**:

**InstInfer**:
- 把decoding阶段attention compute和KV cache一起offload到CSD
- 利用CSD内部高带宽，减少PCIe搬运
- 13B模型 + A6000 GPU上相比FlexGen提升11.1×

**HILOS** (2026):
- Near-storage processing方案
- KV cache相关操作offload到近存储加速器
- 相比基线7.86× throughput，降低85% energy

**HillInfer**:
- 面向commodity PC的长上下文推理
- SmartSSD内部做KV cache eviction/token evaluation
- 减少PCIe数据搬运

**对SSD/固件的要求**:
- KV cache object metadata支持
- Token importance/eviction hint
- In-storage scan/top-k/attention pre-processing
- Host-device协同调度接口
- SmartSSD/DPU/FPGA/ASIC near-data path

### 4️⃣ CXL Memory + Processing-Near-Memory

**定位**:
```
HBM: 最快，但贵、容量小
DDR: 较大，但CPU-GPU PCIe访问受限
CXL memory: 可扩展、可池化、适合做中间memory tier ⭐
SSD: 容量最大，但延迟/带宽更差
```

**代表工作**: CXL-enabled KV-cache管理（2025）
- 用CXL memory expansion扩大GPU系统容量
- 引入PNM在CXL memory内做token page selection
- 目标1M-token LLM inference
- 支持更大的GPU batch size

**训练场景**: CXL-attached memory增强长上下文LLM fine-tuning

**分层策略**:
```
Hot KV / active tensors → HBM
Warm KV / optimizer / activation → CXL / DRAM
Cold KV / persistent prefix cache / RAG index → SSD
```

**对SSD的影响**:
- CXL吃掉部分"SSD做内存扩展"场景
- SSD重点打cold/warm cache、持久化、低成本容量、跨进程共享
- 不与CXL拼延迟

### 5️⃣ KV Cache压缩、选择、淘汰

**核心理念**: 先减少要offload的数据

**主要技术**:
- KV quantization
- KV pruning
- Token eviction
- Importance-aware KV selection
- Dynamic sparse attention
- Cache recomputation vs retrieval tradeoff

**代表工作**:

**RocketKV** (2025):
- 两阶段KV cache压缩
- 永久token eviction + 动态KV token selection
- 加速decode阶段

**LeoAM**:
- 面向单张消费级GPU
- Importance-aware long-context inference
- GPU-CPU-Disk自适应分层KV管理

**TurboQuant** (Google):
- KV cache压缩到3 bit
- 显存降低6×以上
- H100上最高8× attention logits计算加速

**NVFP4** (NVIDIA Blackwell):
- 相比FP8进一步降低50% KV footprint
- 支持更长context或更大batch

**与SSD offloading的组合**:
```
先压缩/选择/淘汰
  ↓
再offload到CPU/SSD/CXL
  ↓
需要时只取重要KV或压缩KV
```

**对SSD benchmark的影响**:
- Compressed KV block
- Variable-size object
- Importance-aware sparse read
- Hot/cold block混合访问

### 6️⃣ CPU-GPU Hybrid Execution

**核心理念**: Offload部分attention compute到CPU

**代表工作**:

**NEO** (2025):
- 部分attention compute和KV cache从GPU offload到本地CPU
- Asymmetric GPU-CPU pipelining
- Load-aware scheduling
- 提升batch size和吞吐

**HybridGen** (2026):
- Hybrid attention framework
- CPU-GPU协同支持长上下文推理
- 充分利用硬件

**APEX** (2025):
- Profiling-informed scheduling
- 预测CPU/GPU子任务执行时间
- 动态分配任务
- 最大化CPU-GPU overlap

**对SSD的启发** - 多consumer访问:
- GPU read
- CPU read
- DPU read
- SmartSSD internal access
- Remote RDMA read

### 7️⃣ MoE Expert Offloading

**特点**: MoE参数大，但每个token只激活部分expert

**代表工作**:

**Fiddler** (ICLR 2025):
- 本地设备MoE推理
- CPU-GPU orchestration
- 单张24GB GPU运行未量化Mixtral-8x7B (90GB+参数)
- 达到3+ token/s

**MoE-Lightning**:
- 内存受限设备高吞吐MoE推理
- Hierarchical roofline model
- 单张T4 16GB上Mixtral 8x7B相比baseline提升10.3× throughput

**SpecOffload**:
- Speculative decoding嵌入offloading
- 利用GPU等数据时的潜在空闲算力

**争议**: 
- SSD读能耗可能显著高于DRAM
- Decode阶段频繁加载expert时不能只看容量成本
- vLLM工程实现还未达到理想的"按gated expert动态加载"

**对SSD的关注点**:
- Expert weight object预取
- Gating-aware prefetch
- Batch内expert locality
- 大块读 + 随机expert访问
- 读能耗/token
- 热expert缓存

### 8️⃣ 训练阶段Offloading

**重点**: Activation / Optimizer / Tensor lifetime

**代表工作**:

**TERAIO** (NeurIPS 2025):
- GPUDirect Storage和SSD做GPU memory expansion
- Lifetime-aware tensor offloading
- Active tensors只占allocated GPU memory一小部分
- Inactive tensors很大且很久不用

**Multi-level, multi-path offloading** (2025):
- FSDP主要offload到host memory
- DeepSpeed、Colossal-AI支持NVMe offloading
- I/O overhead可能进入training critical path

**SSDTrain**:
- Activation offloading到NVMe SSD
- I/O与GPU compute overlap
- 降低peak activation memory

**I/O形态差异**:
```
推理KV: 大量中小块random read，p99延迟关键
训练tensor: 大tensor顺序/半顺序读写，带宽和overlap关键
Optimizer offload: 大容量、周期性读写、写放大和耐久关键
```

**Benchmark应分开**:
- Inference KV benchmark
- Training tensor offload benchmark
- Optimizer state offload benchmark
- Activation checkpoint/offload benchmark

### 9️⃣ Distributed KV Cache / Context Memory

**背景**: KV cache从单机缓存变成跨实例、跨节点、跨存储系统共享的context memory

**代表工作**:

**llm-d** (2026):
- KV cache offload到任意filesystem
- 解决分布式vLLM实例间KV cache本地化问题
- 扩大cache scale
- 可插拔KV-cache aware routing服务

**NVIDIA BlueField-4 CMX/STX**:
- 产业级方案
- DPU + 网络 + NVMe + KV cache/context memory
- 用于agentic AI的长上下文存储层

**新benchmark需求**:
- Local SSD cache hit
- Remote SSD cache hit
- Cross-node KV migration
- Cache-aware routing
- KV cache consistency/eviction
- Multi-tenant isolation

**定位转变**: SSD从单机盘变成inference cluster的context cache tier

## 🔧 对AI SSD固件的6个关键启发

### 1. KV block size不再是4K

**新benchmark重点**:
- 16K random read
- 64K random read
- 128K random read
- 256K random read
- Variable-size random read

**原因**: KV cache object、expert weight shard、RAG chunk都不是传统4K DB workload

### 2. Read p99/p999比平均带宽重要

**长上下文decode中**: 某一次KV read长尾会造成GPU/NPU stall

**固件优化重点**:
- Read tail latency
- GC interruption
- Read/write arbitration
- Thermal throttling下的latency stability

### 3. Mixed workload是核心

**真实场景**:
```
前台: KV read / RAG query
后台: snapshot / index build / cache writeback
同时: 模型加载 / 日志 / checkpoint
```

**设计要求**:
- Foreground read + background write
- KV read + cache eviction write
- RAG query + index compaction
- Model load + system update

### 4. Host hint / Stream hint的重要性

**AI workload天然区分**:
- Hot KV
- Cold KV
- Persistent prefix cache
- Temporary activation
- Optimizer state
- Expert weight
- RAG index
- Recall snapshot

**固件可优化**:
- 冷热分离
- 不同GC策略
- 不同SLC cache policy
- 不同read priority
- 不同wear leveling策略

### 5. 新I/O路径

**未来路径**:
- GPU ↔ SSD
- GPU ↔ DPU ↔ SSD
- GPU ↔ CXL memory ↔ SSD
- SmartSSD内部计算后返回小结果

**测试需求**:
- GDS read latency
- GPU buffer direct read
- NVMe queue depth from GPU runtime
- SGL/PRP path
- DPU-mediated KV cache access

### 6. Energy/token成为新指标

**原因**: MoE expert SSD offload的SSD读能耗可能让decode阶段不划算

**Benchmark应记录**:
- J/token
- J/query
- J/1M tokens
- SSD active power
- Thermal throttling point
- QoS under power cap

## 📚 重点跟踪的代表工作

| 方向 | 代表工作/系统 | 关注重点 |
|------|-------------|---------|
| GPU-centric SSD KV | Tutti | GPU发起I/O、SSD-backed KV实用化 |
| 开源KV cache层 | LMCache | vLLM/SGLang KV抽取、共享、offload |
| 生产级KV offload | NVIDIA Dynamo | CPU/SSD/network storage分层 |
| 分布式KV cache | llm-d | Filesystem-backed KV、跨节点共享 |
| In-storage compute | InstInfer/HILOS/HillInfer | SmartSSD、near-storage attention |
| CXL/PNM | CXL-enabled KV cache | 1M token、CXL memory page selection |
| KV压缩选择 | RocketKV/LeoAM/TurboQuant | 少搬数据，压缩后offload |
| CPU-GPU hybrid | NEO/HybridGen/APEX | Offload compute而不只是data |
| MoE expert offload | Fiddler/MoE-Lightning | Expert locality、prefetch、能耗 |
| 训练offload | TERAIO/SSDTrain | Tensor lifetime、activation、optimizer |

## 🎯 核心结论

**一句话总结**: 
> Offloading的下一阶段不是"更大容量"，而是"让GPU/NPU不因为数据搬运停下来"。

**对AI SSD最有价值的方向**:
1. SSD-backed KV cache
2. Near-storage / in-storage attention
3. 64K~256K random read p99优化
4. Mixed read/write QoS
5. GDS / GPU-centric I/O path
6. CXL + SSD多层memory hierarchy
7. RAG / agent / long-context的真实trace benchmark

## 🔗 相关概念

- [[kv-cache|KV缓存]]
- [[tutti|Tutti系统]]
- [[lmcache|LMCache]]
- [[gpu-direct-storage|GPU Direct Storage]]
- [[cxl-memory|CXL Memory]]
- [[smart-ssd|SmartSSD]]
- [[moe-models|MoE模型]]
- [[near-storage-compute|近存储计算]]

## 🔗 相关实体

- [[vllm|vLLM]]
- [[nvidia|NVIDIA]]
- [[sglang|SGLang]]

---

*摄取日期: 2026-06-04*
*来源: LLM/AI系统Offloading技术深度分析*
