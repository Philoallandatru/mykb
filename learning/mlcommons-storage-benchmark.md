# MLCommons Storage Benchmark 学习笔记

## 核心洞察

MLCommons Storage Benchmark Suite 代表了**机器学习存储性能测试的行业标准**。它不是简单地测试存储的原始性能，而是模拟真实 ML 工作负载的 I/O 模式，提供了从数据中心到提交认证的完整方法论。

---

## 1. 标准化 Benchmark 的价值：为什么需要 MLPerf Storage

### 问题背景

**传统存储 benchmark 的局限**：
- FIO 测试原始 I/O（顺序读写、4K random）
- 不反映真实应用的 I/O 模式
- 不包含应用层开销（序列化、解压、数据预处理）
- 难以对比不同存储系统在 ML 场景下的表现

**ML 工作负载的特殊性**：
- 大文件顺序读（训练数据加载）
- 大文件顺序写（checkpoint 保存）
- 小块随机读（KV cache、向量检索）
- 混合读写（向量库构建）
- 高并发（分布式训练、多用户推理）

### MLCommons Storage 的解决方案

**真实 workload 模拟**：
```
Training: 模拟 FLUX.1/RetinaNet/DLRMv2 的数据加载模式
Checkpointing: 模拟 Llama3 8B~1250B 的 checkpoint 读写
VectorDB: 模拟 Milvus 的向量插入和检索
KVCache: 模拟 LLM 推理的 KV cache 卸载
```

**包含应用层开销**：
- 数据序列化/反序列化
- 压缩/解压
- 数据预处理（resize, augmentation）
- 向量化计算（embedding）

**标准化对比**：
- CLOSED 提交：严格限制更改，确保公平对比
- OPEN 提交：允许优化，探索极限性能
- 规范化指标：GB/s/RU, GB/s/KW（不只是绝对性能）

**Why**:
1. **原始 I/O 性能不等于应用性能** - 应用层开销可能占 30-50%
2. **ML workload 有独特的 I/O 模式** - 与传统企业应用不同
3. **标准化才能公平对比** - 避免"作弊"或cherry-picking场景
4. **行业认可度** - MLPerf 是 AI 基础设施的金标准

**How to apply**:
- 评估存储系统时，使用 MLCommons Storage 而不只是 FIO
- 关注与自己业务最相关的 workload（训练、推理、RAG等）
- 参考 CLOSED 提交结果进行产品选型
- 参考 OPEN 提交了解优化潜力

---

## 2. 四大 Workload 的设计智慧

### 选择这四个 workload 的原因

**Training**：
- ML 最基础的场景
- 数据加载是训练的瓶颈之一（GPU 可能在等数据）
- 代表性模型：CV (FLUX.1), 检测 (RetinaNet), 推荐 (DLRMv2)

**Checkpointing**：
- 大规模训练的必需功能
- 故障恢复时间影响训练效率
- Llama3 8B~1250B 覆盖从小到超大规模

**VectorDB**：
- RAG 的核心基础设施
- 向量检索是 LLM 应用的关键路径
- Milvus 是开源代表，DiskANN/HNSW 是主流算法

**KVCache**：
- 长上下文 LLM 的瓶颈
- 存储层成为 memory hierarchy 的一部分
- 直接影响推理延迟和吞吐量

**Why**:
1. **覆盖 ML 全生命周期** - 训练 → 检查点 → 推理（VDB + KVCache）
2. **代表不同 I/O 模式** - 大文件顺序、小块随机、混合读写
3. **行业痛点** - 每个都是真实的性能瓶颈
4. **可扩展** - 未来可以增加新 workload（如多模态、RL）

**How to apply**:
- 根据自己的业务场景选择最相关的 workload
  - CV/NLP 训练 → Training
  - LLM 训练 → Checkpointing
  - RAG 应用 → VectorDB
  - LLM 长上下文推理 → KVCache
- 如果业务涉及多个场景，全部测试
- 关注瓶颈场景，不要被非关键路径的性能误导

---

## 3. CLOSED vs OPEN 提交：两种评估哲学

### CLOSED 提交

**规则**：
- 严格限制可修改的部分
- 只能调整特定配置参数
- 不能修改代码、算法、数据格式

**目标**：
- 公平对比不同存储系统
- 避免"作弊"（如预加载数据到内存）
- 确保结果可重复

**适用场景**：
- 产品选型（对比 Lustre vs WekaFS vs GPFS）
- 供应商评估（选择云存储服务）
- 官方排行榜（MLPerf Storage Leaderboard）

### OPEN 提交

**规则**：
- 允许任何优化
- 可以修改代码、算法、配置
- 需要详细说明所做的更改

**目标**：
- 探索存储系统的最大潜力
- 鼓励创新优化
- 推动技术进步

**适用场景**：
- 研究新技术（如 GPU Direct Storage, io_uring）
- 优化现有系统
- 展示极限性能

### 两者的平衡

**为什么需要两种提交类型**：

| 维度 | CLOSED | OPEN |
|------|--------|------|
| **可比性** | 高 | 低 |
| **创新性** | 低 | 高 |
| **公平性** | 高 | 取决于披露程度 |
| **实用价值** | 选型决策 | 技术探索 |

**Why**:
1. **CLOSED 保证公平** - 避免各说各话
2. **OPEN 推动进步** - 不限制创新
3. **两者互补** - CLOSED 看现状，OPEN 看潜力

**How to apply**:
- 选型时主要看 CLOSED 结果
- 优化时参考 OPEN 的方法
- 提交时根据目的选择类型：
  - 想证明产品性能 → CLOSED
  - 想展示技术突破 → OPEN

---

## 4. 性能规范化指标的重要性

### 为什么不只看绝对性能

**数据中心的现实约束**：
```
空间约束：机房只有这么多机架位（Rack Units）
电力约束：每个机房有功率上限（KW）
成本约束：空间和电力都是钱
```

**单纯的绝对性能误导决策**：
```
系统 A: 100 GB/s, 占用 10 RU, 功耗 5 KW
系统 B: 80 GB/s, 占用 2 RU, 功耗 1 KW

绝对性能: A > B
GB/s/RU: A=10, B=40  (B 获胜)
GB/s/KW: A=20, B=80  (B 获胜)
```

### 规范化指标

**机架单元效率（GB/s/RU, IOPs/RU）**：
- 衡量空间利用效率
- 高密度系统的优势
- 适合空间受限的数据中心

**功率效率（GB/s/KW, IOPs/KW）**：
- 衡量能耗效率
- 绿色数据中心的关键指标
- 适合电力成本高的地区

**TCO（Total Cost of Ownership）**：
```
TCO = 硬件成本 + 空间成本 + 电力成本 + 维护成本
```

规范化指标直接影响 TCO 的后三项。

**Why**:
1. **绝对性能忽略了资源成本** - 数据中心不是无限的
2. **不同场景有不同约束** - 有的限空间，有的限电力
3. **规范化指标反映真实价值** - 每单位资源的产出

**How to apply**:
- 评估存储系统时，同时看绝对性能和规范化指标
- 根据自己的约束选择优化目标：
  - 空间受限 → 优化 GB/s/RU
  - 电力受限 → 优化 GB/s/KW
  - 预算充足 → 优化绝对性能
- 计算 TCO 时，使用规范化指标估算运营成本

---

## 5. 为什么不需要 GPU：存储 vs 计算的分离

### 设计哲学

**MLCommons Storage 的定位**：
```
测试目标: 存储系统性能
测试方法: 模拟 ML workload 的 I/O 模式
测试环境: CPU + 存储（不需要 GPU）
```

**为什么 CPU 足够**：
1. **I/O 模式可以用 CPU 模拟** - DLIO benchmark
2. **GPU 计算不是瓶颈** - 测试的是存储，不是训练速度
3. **降低测试成本** - GPU 很贵，不是每个存储团队都有
4. **简化部署** - CPU 环境更容易搭建

### 与真实训练的区别

**真实训练**：
```
读取数据 → 预处理 → GPU 计算 → 更新权重
       ↑ 存储瓶颈          ↑ 计算瓶颈
```

**MLCommons Storage 测试**：
```
读取数据 → 预处理 → (模拟计算延迟) → 下一个 batch
       ↑ 测试这部分
```

**模拟方法**：
- 使用 DLIO 生成真实的 I/O pattern
- 记录数据读取和预处理的时间
- 不实际训练模型（节省时间）

**Why**:
1. **分离关注点** - 存储测试不应该被 GPU 性能干扰
2. **降低成本** - CPU 测试环境比 GPU 便宜得多
3. **通用性** - 不依赖特定 GPU 型号

**How to apply**:
- 理解 benchmark 的局限性：
  - ✅ 可以评估存储在 ML 场景的性能
  - ❌ 不能评估端到端训练性能（需要 GPU）
  - ❌ 不能测试 GPU Direct Storage（需要 GPU）
- 如果需要测试 GDS，使用其他工具（如 [[lmcache|LMCache]] 实测）

---

## 6. 与 AI SSD Benchmark 的对比与互补

### 定位差异

| 维度 | MLCommons Storage | AI SSD Benchmark |
|------|-------------------|------------------|
| **规模** | 数据中心级 | 单机 PC 级 |
| **场景** | 训练/检查点/VDB/KVCache | 模型加载/RAG/Recall/KVCache |
| **标准化** | MLPerf 官方标准 | 内部或厂商标准 |
| **目标用户** | 云厂商、HPC中心、存储厂商 | AI PC 用户、SSD 厂商 |
| **存储类型** | Lustre/GPFS/S3 等企业级 | 本地 NVMe SSD |
| **测试工具** | Python + DLIO | fio + 真实应用 |

### 共同点

**KV Cache 场景**：
- 两者都关注 KV cache 作为存储层
- 都测试 64KB~256KB 的小块随机读
- 都关注 p99 延迟

**方法论相似**：
- 都采用分层 benchmark 架构
- 都模拟真实应用的 I/O 模式
- 都关注延迟分布而不只是平均值

### 互补关系

**MLCommons Storage 的优势**：
- ✅ 标准化，行业认可
- ✅ 覆盖数据中心场景
- ✅ 官方维护，持续更新

**AI SSD Benchmark 的优势**：
- ✅ 针对 AI PC 场景
- ✅ 包含 Recall、多模态等 PC 特有场景
- ✅ 更轻量，易于执行

**如何结合使用**：
```
数据中心存储评估:
  使用 MLCommons Storage

AI PC SSD 评估:
  使用 AI SSD Benchmark

方法论借鉴:
  AI SSD Benchmark ← MLCommons Storage
  (workload 设计、指标定义、提交规则)
```

**Why**:
1. **不同规模需要不同 benchmark** - 数据中心 vs PC
2. **标准化推动行业发展** - MLPerf 的影响力
3. **方法论可以迁移** - 核心原则是一致的

**How to apply**:
- 如果在设计 AI SSD Benchmark，借鉴 MLCommons Storage 的：
  - 分层 workload 设计
  - CLOSED/OPEN 提交类型
  - 规范化指标（GB/s/RU → GB/s/W for AI PC）
  - 提交指南和规则
- 如果在评估数据中心存储，直接使用 MLCommons Storage
- 如果在评估 AI PC SSD，使用 AI SSD Benchmark 或自己设计

---

## 7. DLIO Benchmark 的集成价值

### DLIO 是什么

**Deep Learning I/O Benchmark**：
- 专门模拟深度学习的 I/O 模式
- 支持各种数据格式（TFRecord, HDF5, JPEG, PNG, NPY）
- 模拟数据预处理和 augmentation
- 不实际训练模型（只关注 I/O）

### 为什么 MLCommons Storage 集成 DLIO

**直接生成 I/O pattern 的困难**：
```python
# 想模拟训练数据加载，需要考虑：
- 文件格式（TFRecord/HDF5/图片）
- 读取顺序（顺序/随机/shuffle）
- Batch 大小
- 数据预处理（resize, normalize, augment）
- 多进程/多线程
- Prefetch 策略
```

手写这些代码复杂且容易出错。

**DLIO 的价值**：
- 已经实现了常见 DL 框架的 I/O 模式
- 可配置性强（workload, format, batch size, prefetch）
- 经过验证，接近真实训练的 I/O

**集成方式**：
```bash
# MLCommons Storage 的 Training workload 内部调用 DLIO
mlpstorage --workload training --model retinanet
  ↓
  调用 DLIO 生成 RetinaNet 的 I/O pattern
  ↓
  测量存储系统的响应性能
```

**Why**:
1. **真实性** - DLIO 的 I/O pattern 接近真实训练
2. **复用** - 不需要重新造轮子
3. **可维护** - DLIO 团队持续优化

**How to apply**:
- 如果要测试 ML 存储性能，考虑使用 DLIO
- 如果要设计新的 ML benchmark，考虑集成 DLIO
- 理解 DLIO 的配置参数，调整到符合自己的场景

---

## 8. 提交流程的严谨性

### MLPerf 提交要求

**必需材料**：
1. **系统配置文件**（`system_configuration.yaml`）
   - 硬件配置（CPU, 内存, 存储, 网络）
   - 软件配置（OS, 内核, 文件系统, 驱动）
   - 网络拓扑

2. **测试结果**
   - 所有 workload 的性能数据
   - 原始日志文件
   - 监控数据（可选但推荐）

3. **提交文档**
   - 按照 `Submission_guidelines.md` 格式
   - 说明所有配置和优化
   - OPEN 提交需详细说明修改内容

4. **可重复性证明**
   - 提供复现步骤
   - 至少运行 3 次取平均值
   - 提供标准差

### 为什么这么严格

**保证结果的可信度**：
- 避免"作弊"（如预加载数据到内存）
- 避免cherry-picking（只报最好的结果）
- 确保其他人可以复现

**建立行业标准**：
- 统一的提交格式
- 统一的评估标准
- 可对比的结果

**Why**:
1. **没有严格流程就没有公信力** - 否则大家都自说自话
2. **可重复性是科学的基础** - benchmark 结果必须可验证
3. **详细文档帮助理解** - 不只是数字，还要知道怎么来的

**How to apply**:
- 如果要提交 MLPerf 结果：
  - 提前阅读 `Submission_guidelines.md`
  - 准备好所有材料
  - 多次运行确保稳定性
- 如果在设计内部 benchmark：
  - 借鉴 MLPerf 的提交流程
  - 要求提供系统配置和原始日志
  - 建立可重复性检查

---

## 9. 从 MLCommons Storage 学到的 Benchmark 设计原则

### 原则 1：真实 Workload 优于人工 Pattern

**反例**：FIO 只测 4K random read
**正例**：MLCommons Storage 模拟 FLUX.1 训练的数据加载

**Why**: 真实应用的 I/O 模式复杂，不能用简单 pattern 代表

### 原则 2：包含应用层开销

**反例**：只测块设备层的吞吐量
**正例**：包含序列化、解压、预处理的时间

**Why**: 用户感知的是端到端性能，不是块设备性能

### 原则 3：标准化才能对比

**反例**：每个厂商用自己的测试方法
**正例**：CLOSED 提交严格限制可修改部分

**Why**: 没有统一标准，结果无法对比

### 原则 4：分层设计满足不同需求

**反例**：只有一种提交类型
**正例**：CLOSED（公平对比）+ OPEN（创新优化）

**Why**: 不同用户有不同目的

### 原则 5：规范化指标反映真实价值

**反例**：只看绝对性能
**正例**：GB/s/RU, GB/s/KW

**Why**: 资源有限，需要考虑效率

### 原则 6：详细文档和严格流程

**反例**：只提交数字
**正例**：系统配置 + 测试结果 + 原始日志 + 复现步骤

**Why**: 可信度需要透明度

### 原则 7：持续演进

**反例**：一次性设计，不再更新
**正例**：MLCommons Storage 持续增加新 workload

**Why**: ML 技术快速发展，benchmark 需要跟上

---

## 10. 实战应用：如何使用 MLCommons Storage

### 场景 1：评估并行文件系统（Lustre vs WekaFS）

**步骤**：
1. 在两个系统上部署 MLCommons Storage
2. 运行所有 4 个 workload（CLOSED 模式）
3. 对比结果：
   - Training: 数据加载吞吐量
   - Checkpointing: checkpoint 保存/加载速度
   - VectorDB: 向量插入和检索延迟
   - KVCache: KV cache 读写性能
4. 计算规范化指标（GB/s/RU, GB/s/KW）
5. 根据实际业务需求（训练为主 vs 推理为主）选择

### 场景 2：优化现有存储系统

**步骤**：
1. 运行 MLCommons Storage 找到瓶颈
2. 分析哪个 workload 性能最差
3. 针对性优化：
   - Training 慢 → 优化大文件顺序读
   - Checkpointing 慢 → 优化大文件顺序写
   - VectorDB 慢 → 优化小块随机读写混合
   - KVCache 慢 → 优化 64KB~256KB 随机读
4. 使用 OPEN 模式测试优化效果
5. 如果优化显著，可以提交 OPEN 结果展示

### 场景 3：为 AI SSD Benchmark 借鉴方法论

**可借鉴的部分**：
1. **Workload 设计**：
   - 从真实应用场景出发
   - 定义清晰的 I/O 模式
   - 提供参考实现

2. **提交类型**：
   - CLOSED: 标准配置，公平对比
   - OPEN: 优化配置，展示潜力

3. **规范化指标**：
   - GB/s/W (每瓦性能) for AI PC
   - IOPS/W (每瓦 IOPS)

4. **提交指南**：
   - 系统配置模板
   - 结果格式定义
   - 可重复性要求

---

## 核心结论

MLCommons Storage Benchmark Suite 提供了**ML 存储性能测试的黄金标准**。

关键 takeaway：
1. **真实 workload 才能反映真实性能** - 不要只测 FIO
2. **标准化推动行业发展** - MLPerf 的权威性
3. **CLOSED/OPEN 双轨制平衡公平与创新** - 各有价值
4. **规范化指标反映 TCO** - GB/s/RU 和 GB/s/KW 很重要
5. **CPU 足够测存储** - 不需要 GPU（除非测 GDS）
6. **DLIO 提供真实 I/O 模式** - 复用而不是重造轮子
7. **严格流程保证可信度** - 详细文档和可重复性
8. **与 AI SSD Benchmark 互补** - 不同规模，共同目标

这套方法论可以指导任何存储 benchmark 的设计，从数据中心到 AI PC。


## 相关概念

- [[ai-ssd]]
- [[nvme-ssd]]
- [[mlcommons-storage]]
