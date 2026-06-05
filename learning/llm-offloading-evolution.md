---
type: learning
category: 系统架构
status: in-progress
progress: 30
started: 2026-06-04
updated: 2026-06-04
tags:
  - learning
  - offloading
  - ai-systems
  - research-overview
---

# LLM Offloading技术演进学习笔记

## 📚 来源

**类型**: 技术综述  
**范围**: 截至2026年6月的LLM/AI系统offloading研究  
**深度**: 9个主要方向 + 6个工程启发  

## 📝 关键要点

### 1. Offloading的范式转变 ✅

**传统认知** (错误):
> Offloading = 显存不够，把数据放到CPU/SSD

**现代理解** (正确):
> Offloading = 在HBM/DRAM/CXL/SSD多层次间优化数据放置、移动时机、压缩策略、计算位置的系统工程

**5代演进**:
```
1.0: 权重offload → 能跑起来
2.0: KV cache offload → 长上下文
3.0: 分布式cache → 降低TTFT
4.0: 近存储计算 → 减少数据搬运
5.0: 联合优化 → 准确率/延迟/成本/能耗平衡
```

**启示**: 
- 不是单一技术，是系统性问题
- 每一代都在解决上一代的新瓶颈
- 未来是多技术融合

### 2. KV Cache成为核心战场 ✅

**为什么KV Cache特殊**:

| 对比维度 | 模型权重 | KV Cache |
|---------|---------|----------|
| 大小 | 固定 | 随context长度线性增长 |
| 访问模式 | 顺序读取 | 随机读取 |
| 生命周期 | 全程需要 | 可共享、可驱逐 |
| 可压缩性 | 低 | 高 (3-8 bit) |
| 可计算性 | 否 | 是 (attention) |

**核心挑战**:
```
batch size ↑ + context length ↑ + layers ↑
  ↓
KV cache >> GPU HBM
  ↓
必须offload，但如何不拖慢推理？
```

**解决方向演进**:
1. **朴素方案**: GPU → CPU/SSD (慢)
2. **改进方案**: 分层缓存 + LRU驱逐 (LMCache)
3. **激进方案**: GPU直接控制SSD I/O (Tutti)
4. **终极方案**: 在SSD/CXL内部先计算 (InstInfer/HILOS)

**个人理解**:
- KV cache像"可计算的数据"，不只是"需要搬的数据"
- 最优策略不是"更快搬"，而是"少搬甚至不搬"
- 与[[lmcache-stress-test-learning|LMCache实验]]呼应

### 3. 内存层次不再是二元 ✅

**传统架构** (过时):
```
GPU HBM (快但小)
  vs
CPU/SSD (慢但大)
```

**现代架构** (正确):
```
GPU HBM (40-80 GB)
  ↓ ~100 GB/s
CPU DRAM (数百GB)
  ↓ ~50 GB/s
CXL Memory (TB级, 池化, 可共享)
  ↓ ~10 GB/s
Local SSD (TB级)
  ↓ ~1 GB/s (网络)
Remote Storage (PB级)
```

**关键洞察**:
1. **不是替代关系，是分工关系**
   - HBM: active tensors, 热KV
   - CXL: warm KV, optimizer states
   - SSD: cold KV, prefix cache, RAG index

2. **每层都有最优场景**
   - CXL不会杀死SSD
   - SSD不会被CXL完全替代
   - 关键是"数据放哪一层最经济"

3. **分层标准是访问频率和延迟容忍度**
   - Hot path → HBM
   - Warm path → CXL/DRAM
   - Cold path → SSD
   - Archive → Remote storage

**与[[kv-cache|KV缓存]]的联系**:
- KV cache的不同部分适合不同层
- 动态分层比静态分配更优

### 4. 近存储计算的颠覆性 ✅

**传统范式**:
```
数据在哪 → 搬到计算附近 → 计算
```

**近存储范式**:
```
数据在哪 → 在数据附近计算 → 只搬结果
```

**案例**: InstInfer在SmartSSD内做attention

**收益分析**:
```
传统: 
  SSD读15K tokens KV (几百MB)
    ↓ PCIe 带宽受限
  GPU做attention
    ↓
  返回结果 (几KB)

InstInfer:
  SmartSSD内部做partial attention
    ↓ 内部高带宽
  只返回top-K结果 (几十KB)
    ↓ PCIe几乎不占用
  GPU做final attention
```

**为什么现在可行**:
1. SmartSSD/DPU/FPGA成本下降
2. NVMe协议扩展支持
3. LLM attention可分解
4. Token importance可量化

**工程现实**:
- 不是所有操作都适合near-storage
- 需要host runtime、firmware、LLM框架协同设计
- 标准化还在进行中

**启示**:
> 未来的AI SSD不只是"存储设备"，而是"计算+存储一体化节点"

### 5. 压缩优先于搬运 ✅

**核心思想**:
```
朴素: 生成100GB KV → offload 100GB
聪明: 生成100GB KV → 压缩到10GB → offload 10GB
更聪明: 生成100GB KV → 选择重要20GB → 压缩到2GB → offload 2GB
```

**压缩技术栈**:

| 技术 | 压缩比 | 精度损失 | 适用阶段 |
|------|--------|---------|---------|
| FP16 → FP8 | 2× | 微小 | 所有 |
| FP8 → FP4 (NVFP4) | 2× | 可接受 | Decode |
| FP8 → INT3 (TurboQuant) | 2.67× | 无 (谷歌声称) | Decode |
| Token pruning | 2-10× | 依赖算法 | Prefill+Decode |
| KV selection | 5-20× | 可控 | Long context |

**组合效果**:
```
原始: 100 GB KV
  ↓ FP16 → INT4
压缩: 25 GB
  ↓ Token selection (保留20%)
选择: 5 GB
  ↓ Offload到SSD
最终: 只搬5GB，95%数据未搬运
```

**关键判断**:
- **压缩是offloading的前置步骤，不是替代方案**
- 压缩后的数据仍需要分层存储
- 但offload开销大幅下降

**与[[lru-cache|LRU驱逐]]的关系**:
- 压缩减少了需要驱逐的频率
- 但驱逐策略仍然必要

### 6. 多consumer访问模式 ✅

**传统假设** (错误):
> SSD只服务单一主机上的单一GPU

**现代现实** (正确):
```
同一SSD上的数据可能被访问自:
- 本地GPU (推理)
- 本地CPU (hybrid attention)
- 本地DPU (routing决策)
- SmartSSD内部处理器 (pre-processing)
- 远程节点 (cache sharing)
```

**案例**: NEO系统
- 部分attention在CPU
- 部分attention在GPU
- KV cache在SSD
- CPU和GPU并发读取不同KV块

**工程挑战**:
1. **并发控制**: 谁先读？如何仲裁？
2. **QoS保证**: GPU read不能被CPU read阻塞
3. **缓存一致性**: 多级cache如何同步？
4. **带宽分配**: 如何公平或按优先级分配？

**固件需求**:
- 多queue支持
- Per-queue QoS
- Priority-aware scheduling
- Fairness算法

### 7. 能耗成为一等公民指标 ✅

**传统指标** (不完整):
- 延迟 (TTFT, latency)
- 吞吐量 (tokens/s, requests/s)
- 成本 ($/token)

**新增关键指标**:
- **能耗/token** (J/token)
- **能耗/query** (J/query)
- **总拥有能耗** (J/1M tokens)

**为什么重要**:

**案例1**: MoE expert SSD offload
```
方案A: 全部放GPU HBM
  - 延迟: 低
  - 能耗: GPU idle功耗 × 时间

方案B: Expert offload到SSD
  - 延迟: 中等
  - 能耗: SSD读能耗可能 > GPU idle节省的能耗
  
结论: Offload未必省能耗！
```

**案例2**: 数据中心尺度
```
1M tokens @ 全GPU HBM:
  - GPU数量: 少
  - GPU利用率: 高
  - 总能耗: 基准

1M tokens @ SSD offload:
  - GPU数量: 可能更多 (因为单GPU吞吐降低)
  - GPU利用率: 中等
  - SSD读写能耗: 新增
  - 总能耗: 可能更高！
```

**正确的能耗分析**:
```
Total Energy = 
  GPU compute energy +
  GPU idle energy +
  SSD read energy +
  SSD write energy +
  PCIe transfer energy +
  CPU assist energy +
  Cooling energy
```

**启示**:
- Offloading不自动等于省钱/省电
- 需要全链路能耗建模
- 不同workload最优策略不同

## 🔗 相关笔记

### 实践经验
- [[lmcache-stress-test-learning|LMCache实验]] - 印证了KV cache分层的实际效果
- [[tutti-paper-analysis|Tutti论文]] - GPU-centric方案的先驱

### 概念
- [[kv-cache|KV缓存]] - 核心被offload对象
- [[lru-cache|LRU算法]] - 驱逐策略
- [[memory-hierarchy|内存层次结构]]
- [[near-storage-compute|近存储计算]]
- [[gpu-direct-storage|GPU Direct Storage]]

### 工具和系统
- [[lmcache|LMCache]] - 本文重点系统之一
- [[tutti|Tutti]] - GPU-centric代表
- [[vllm|vLLM]] - 集成平台

### 原始材料
- [[.raw/llm-offloading-research-2026|Offloading技术全景分析]]

## 💭 个人思考

### 与实际项目的联系

**本地Excel/CSV + LLM分析MVP**也会遇到类似问题:
```
场景: 分析10GB Excel数据
  ↓
问题: 10GB无法全部放GPU内存
  ↓
方案1: 分批加载 (朴素offload)
方案2: 只索引关键列到GPU (selective loading)
方案3: 先在CPU做预聚合 (near-data processing)
```

**RAG平台**的offloading需求:
```
Embedding index: 100GB
  ↓
Hot queries: Top 1% (1GB) → GPU HBM
Warm queries: Top 20% (20GB) → DRAM
Cold queries: 其余 (79GB) → SSD
```

### 技术选型启发

**何时选择LMCache**:
- ✅ 长上下文推理
- ✅ 重复prefix模式 (客服、RAG)
- ✅ 多实例cache共享
- ⚠️ 需要正确配置 (避免踩坑)

**何时考虑Tutti**:
- ✅ GPU数量多
- ✅ SSD I/O是瓶颈
- ✅ 愿意深度定制
- ⚠️ 较新，生态未成熟

**何时用CXL**:
- ✅ Warm data占比大
- ✅ 多GPU共享内存
- ✅ 预算充足
- ❌ 对cold data不适用

### 研究方向判断

**短期 (1-2年)**:
- LMCache类系统成熟化
- KV压缩标准化
- GPU-centric I/O普及

**中期 (2-5年)**:
- Near-storage compute商用化
- CXL + SSD多层次标准化
- 分布式KV cache成为基础设施

**长期 (5年+)**:
- Processing-in-memory (PIM)
- 神经形态存储
- 完全重新设计的memory hierarchy

### 对AI SSD的启示

**如果要设计AI SSD固件**，优先级:

**P0 (立即需要)**:
1. 64K-256K random read p99优化
2. Mixed read/write QoS
3. GDS路径稳定性

**P1 (近期需要)**:
4. Host hint支持 (hot/cold分离)
5. Multi-queue并发
6. Energy/token监控

**P2 (未来需要)**:
7. In-storage pre-processing接口
8. CXL协同
9. 分布式cache支持

## ✅ 学习任务

### 已完成
- [x] 阅读9个方向概述
- [x] 理解offloading演进范式
- [x] 掌握KV cache核心挑战
- [x] 了解内存层次现代架构

### 进行中
- [ ] 深入研究InstInfer/HILOS论文
- [ ] 理解TurboQuant压缩原理
- [ ] 学习CXL-PNM架构
- [ ] 分析MoE expert offload能耗模型

### 待开始
- [ ] 实践：搭建LMCache + Tutti对比测试
- [ ] 研究：llm-d分布式架构
- [ ] 调研：SmartSSD编程模型
- [ ] 实验：不同workload的能耗profile

## 📈 学习成果

**新知识获得**:
- ✅ Offloading 5代演进框架
- ✅ KV cache为何成为核心战场
- ✅ 近存储计算的颠覆性
- ✅ 压缩优先于搬运的原则
- ✅ 能耗作为一等公民指标

**思维升级**:
- 从"二元对立"到"多层协同"
- 从"数据搬到计算"到"计算靠近数据"
- 从"单一指标优化"到"多目标平衡"

**可应用知识**:
- 本地LLM项目的内存管理策略
- RAG系统的索引分层设计
- AI SSD固件优化方向判断

---

*创建于: 2026-06-04*
*状态: 持续学习中，已建立框架*
