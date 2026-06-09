# VectorDB Benchmark 学习笔记

## 核心洞察

VectorDB Benchmark 是 MLCommons Storage 针对 **RAG 应用**的标准化测试方法。它不只测试向量检索速度，而是评估整个向量数据库的端到端性能，包括数据加载、索引构建、相似度检索和召回率验证。

---

## 1. 召回率（Recall）是向量检索的核心指标

### 什么是召回率

**定义**:
```
Recall@k = |ANN 结果 ∩ 精确结果| / k
```

**示例**:
```
精确 top-10: [id_1, id_5, id_8, id_12, id_15, id_20, id_23, id_27, id_30, id_35]
ANN top-10:  [id_1, id_5, id_8, id_12, id_17, id_20, id_23, id_28, id_30, id_35]

交集: [id_1, id_5, id_8, id_12, id_20, id_23, id_30, id_35] = 8 个
Recall@10 = 8 / 10 = 0.8
```

### 为什么召回率比延迟更重要（在某些情况下）

**RAG 应用的用户体验**:
```
召回率 0.95, 延迟 20ms → 用户满意（答案准确）
召回率 0.70, 延迟 10ms → 用户不满意（答案不相关）
```

**Why**:
1. **低召回率 = 检索错误的文档** - LLM 基于错误信息生成答案
2. **用户更在意答案质量而不是速度** - 20ms vs 10ms 感知差异小
3. **召回率低会破坏信任** - 用户发现答案不靠谱后会停止使用

**How to apply**:
- 设定最低召回率要求（通常 > 0.95）
- 在满足召回率前提下优化延迟
- 使用 p99 召回率而不是平均召回率（worst-case 更重要）
- 绘制 latency-recall 曲线，找到最佳权衡点

---

## 2. Ground Truth 集合（FLAT 索引）的必要性

### FLAT 索引的作用

**FLAT = 精确最近邻（Exact NN）**:
- 不做任何近似
- 暴力计算所有向量的距离
- 结果 100% 准确

**用途**:
- 作为 ANN（近似最近邻）算法的基准
- 验证 ANN 算法的召回率
- 调试 ANN 算法的正确性

### 召回率计算流程

**步骤**:
1. 数据加载阶段创建两个集合：
   - ANN 集合（DiskANN/HNSW/AISAQ）
   - FLAT 集合（ground truth）
2. 测试期间同时查询两个集合
3. 对比结果计算召回率

**代码示例**（概念）:
```python
# 查询向量
query_vector = [0.1, 0.2, ..., 0.5]

# ANN 查询（快速）
ann_results = milvus.search(
    collection="ann_collection",
    data=[query_vector],
    limit=10,
    params={"search_ef": 200}
)

# FLAT 查询（精确但慢）
flat_results = milvus.search(
    collection="flat_collection",
    data=[query_vector],
    limit=10
)

# 计算召回率
ann_ids = set(ann_results[0].ids)
flat_ids = set(flat_results[0].ids)
recall = len(ann_ids & flat_ids) / 10
```

### 如果召回率显示 0.000

**常见原因**:
1. FLAT 集合不存在（忘记 `--auto-create-flat`）
2. FLAT 集合是空的（数据加载失败）
3. 向量维度不匹配（datagen 和 run 使用不同维度）

**排查步骤**:
```bash
# 1. 检查集合是否存在
# 使用 Milvus CLI 或 Web UI

# 2. 重新创建 FLAT 集合
./mlpstorage vectordb datagen \
    --auto-create-flat \
    --force \
    ...

# 3. 确保维度一致
# 使用相同的 --config 参数
```

**Why**:
1. **没有 ground truth 就无法验证正确性** - 不知道 ANN 是否准确
2. **FLAT 查询很慢** - 不适合生产，只用于测试
3. **召回率是 ANN 算法的关键指标** - 没有召回率数据就无法评估

**How to apply**:
- 首次测试时必须启用 `--auto-create-flat`
- FLAT 集合只需创建一次，后续测试可复用
- 定期验证 FLAT 集合的数据完整性

---

## 3. 索引算法选择：DiskANN vs HNSW vs AISAQ

### 三种算法的权衡

| 算法 | 内存需求 | 查询速度 | 召回率 | 索引构建时间 | 适用场景 |
|------|---------|---------|--------|-------------|---------|
| **DiskANN** | 低 | 中 | 高 | 长 | 数据量 > 内存 |
| **HNSW** | 高 | 快 | 高 | 中 | 数据量 < 内存 |
| **AISAQ** | 中 | 中 | 中 | 短 | 存储成本敏感 |

### DiskANN：大规模数据的首选

**特点**:
- 基于磁盘的图索引
- 支持数十亿级别向量
- 内存占用低（只需加载部分图）

**适用场景**:
```
数据量: 1000万+ 向量
内存: 有限（< 64GB）
存储: NVMe SSD
查询: 可接受中等延迟（10-50ms）
```

**优化建议**:
- 使用高速 NVMe SSD
- 调整 `search_list` 参数平衡速度和召回率
- 考虑使用 [[gpu-direct-storage|GPU Direct Storage]] 加速

### HNSW：内存充足时的最快选择

**特点**:
- 完全基于内存的图索引
- 查询速度极快（< 5ms）
- 召回率高（> 0.98）

**适用场景**:
```
数据量: < 1000万 向量
内存: 充足（> 64GB）
查询: 需要极低延迟（< 10ms）
成本: 可接受高内存成本
```

**优化建议**:
- 调整 `ef_construction` 和 `M` 参数
- 使用 `search_ef` 参数平衡速度和召回率
- 预留足够内存避免 OOM

### AISAQ：平衡性能和成本

**特点**:
- AI 优化的标量量化
- 压缩向量减少存储和内存
- 牺牲少量召回率换取成本降低

**适用场景**:
```
数据量: 中等（100万 - 1000万）
成本: 敏感
召回率: 可接受 0.90-0.95
存储: 需要节省空间
```

**Why**:
1. **没有万能的索引算法** - 需要根据场景选择
2. **数据规模决定算法类型** - 大规模必须用 DiskANN
3. **内存是稀缺资源** - HNSW 虽快但贵
4. **召回率和速度的权衡** - 参数调优很重要

**How to apply**:
- 数据量 > 内存 → DiskANN
- 数据量 < 内存 且要求极低延迟 → HNSW
- 成本敏感 → AISAQ
- 使用 sweep 模式测试不同配置找最佳

---

## 4. Latency-Recall 权衡曲线

### 什么是 Latency-Recall 曲线

**定义**: 在不同参数配置下，延迟和召回率的关系曲线

**示例**:
```
search_ef=50:  延迟 8ms,  召回率 0.85
search_ef=100: 延迟 12ms, 召回率 0.92
search_ef=200: 延迟 18ms, 召回率 0.96
search_ef=400: 延迟 30ms, 召回率 0.98
```

**曲线特征**:
- 增加 `search_ef` → 召回率提升，延迟增加
- 存在一个"膝点"（knee point）
- 膝点之后召回率提升缓慢但延迟快速增加

### 如何找到最佳配置

**步骤**:
1. 使用 sweep 模式测试多个 `search_ef` 值
2. 绘制 latency-recall 曲线
3. 设定召回率下限（如 0.95）
4. 在满足下限的配置中选择延迟最低的

**代码示例**:
```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取 sweep 结果
df = pd.read_csv('combined_bench_*.sweep.csv')

# 绘制曲线
plt.figure(figsize=(10, 6))
plt.plot(df['mean_recall'], df['mean_latency_ms'], 'o-')
plt.xlabel('Mean Recall')
plt.ylabel('Mean Latency (ms)')
plt.title('Latency-Recall Trade-off')
plt.grid(True)

# 标记召回率下限
plt.axvline(x=0.95, color='r', linestyle='--', label='Min Recall=0.95')

# 找到最佳配置
best = df[df['mean_recall'] >= 0.95].nsmallest(1, 'mean_latency_ms')
plt.scatter(best['mean_recall'], best['mean_latency_ms'], 
            color='red', s=100, label='Best Config')
plt.legend()
plt.show()

print(f"Best search_ef: {best['search_ef'].values[0]}")
print(f"Latency: {best['mean_latency_ms'].values[0]:.2f} ms")
print(f"Recall: {best['mean_recall'].values[0]:.3f}")
```

**Why**:
1. **单一参数无法反映真实情况** - 需要看权衡
2. **不同应用有不同需求** - 有的优先速度，有的优先准确性
3. **膝点之后性价比低** - 延迟增加但召回率提升有限

**How to apply**:
- 对于延迟敏感应用（实时对话）：找到召回率刚好满足的配置
- 对于准确性敏感应用（法律/医疗）：优先保证高召回率
- 定期重新测试：数据分布变化会影响曲线

---

## 5. 并发度（Concurrency）的影响

### 吞吐量 vs 延迟的权衡

**测试不同并发度**:
```bash
# 1 进程：低 QPS，低延迟
./mlpstorage vectordb run --num-query-processes 1 ...
# QPS: 100, p99 latency: 15ms

# 4 进程：中等 QPS，中等延迟
./mlpstorage vectordb run --num-query-processes 4 ...
# QPS: 350, p99 latency: 25ms

# 16 进程：高 QPS，高延迟
./mlpstorage vectordb run --num-query-processes 16 ...
# QPS: 800, p99 latency: 80ms
```

### QPS 饱和点

**现象**:
```
1 → 2 进程: QPS 翻倍（200）
2 → 4 进程: QPS 翻倍（400）
4 → 8 进程: QPS 增加 1.5× （600）
8 → 16 进程: QPS 增加 1.2× （720）← 饱和点
16 → 32 进程: QPS 增加 1.05× （756）← 超过饱和点
```

**瓶颈**:
- CPU 饱和
- 磁盘 I/O 饱和
- Milvus 内部锁竞争
- 网络带宽

**Why**:
1. **并发不是越多越好** - 超过饱和点后延迟快速增加
2. **找到饱和点就是最佳配置** - 性价比最高
3. **不同系统有不同饱和点** - 需要实测

**How to apply**:
- 测试 1/2/4/8/16/32 进程
- 绘制 QPS-进程数 曲线
- 找到 QPS 增长放缓的点
- 实际部署时略低于饱和点（留出余量）

---

## 6. 磁盘 I/O 监控的价值

### 识别存储瓶颈

**分析 `disk_read_iops` 和 `disk_read_mbps`**:

**场景 1: I/O 饱和**
```
disk_read_iops: 50,000 (接近 SSD 极限)
disk_read_mbps: 3000 MB/s (接近 SSD 极限)
p99_latency_ms: 80 (很高)
```
**结论**: SSD 是瓶颈，需要更快的 SSD 或增加并行度

**场景 2: I/O 未饱和**
```
disk_read_iops: 10,000 (远低于 SSD 极限)
disk_read_mbps: 500 MB/s (远低于 SSD 极限)
p99_latency_ms: 80 (很高)
```
**结论**: SSD 不是瓶颈，问题在 CPU/内存/网络/软件

### 不同索引算法的 I/O 模式

**DiskANN**:
```
disk_read_iops: 高（大量随机读）
disk_read_mbps: 中等
```
特征：小块随机读为主

**HNSW**:
```
disk_read_iops: 低（几乎全在内存）
disk_read_mbps: 低
```
特征：首次加载后几乎无 I/O

**AISAQ**:
```
disk_read_iops: 中等
disk_read_mbps: 中等
```
特征：压缩后读取量减少

**Why**:
1. **I/O 监控直接反映存储压力** - 不需要猜测
2. **不同算法有不同 I/O 模式** - 需要匹配合适的 SSD
3. **I/O 饱和是常见瓶颈** - 特别是 DiskANN

**How to apply**:
- 运行 benchmark 时始终查看 I/O 指标
- 如果 I/O 饱和 → 优化存储层（[[ai-ssd|AI SSD]]）
- 如果 I/O 未饱和 → 优化其他层（CPU/软件）
- 使用 I/O 模式选择合适的索引算法

---

## 7. 与 AI SSD Benchmark 的协同

### 两层优化策略

**应用层（VectorDB Benchmark）**:
- 测试向量数据库的端到端性能
- 关注延迟、召回率、QPS
- 优化索引算法、参数配置

**存储层（AI SSD Benchmark）**:
- 测试 SSD 在 RAG 场景的性能
- 关注 I/O 延迟、吞吐量
- 优化 SSD 固件、配置

### 性能瓶颈定位流程

**步骤**:
1. 运行 VectorDB Benchmark
2. 发现 p99 延迟高（如 80ms）
3. 查看 `disk_read_iops` 和 `disk_read_mbps`
4. 如果接近 SSD 极限 → SSD 瓶颈
5. 运行 [[ai-ssd-benchmark-design|AI SSD Benchmark]] 的 AI-RAG-Query
6. 对比不同 SSD 的性能
7. 选择更快的 SSD 或优化现有 SSD

**示例**:
```
VectorDB Benchmark 结果：
  p99_latency: 80ms
  disk_read_iops: 48,000 (接近 50K 极限)
  
AI SSD Benchmark 结果：
  当前 SSD: 64KB random read p99 = 1.2ms
  更快 SSD: 64KB random read p99 = 0.5ms
  
预期改进：
  新 p99_latency ≈ 80 - (48K * 0.7ms) = 46ms
```

**Why**:
1. **应用层和存储层需要协同优化** - 单独优化一层效果有限
2. **VectorDB Benchmark 发现问题** - AI SSD Benchmark 解决问题
3. **端到端测试反映真实体验** - 不能只看存储层

**How to apply**:
- 先运行 VectorDB Benchmark 建立基线
- 如果存储是瓶颈，运行 AI SSD Benchmark
- 优化后重新运行 VectorDB Benchmark 验证
- 迭代优化直到达到目标

---

## 8. 数据分布（uniform vs normal）的影响

### 两种分布的区别

**Uniform（均匀分布）**:
```python
# 每个维度的值均匀分布在 [0, 1]
vector = [random.uniform(0, 1) for _ in range(1536)]
```

**Normal（正态分布）**:
```python
# 每个维度的值服从正态分布 N(0, 1)
vector = [random.gauss(0, 1) for _ in range(1536)]
```

### 对性能的影响

**Uniform**:
- 向量分布均匀
- 最近邻距离相近
- 召回率稳定
- **适合基准测试**

**Normal**:
- 向量聚集在原点附近
- 最近邻距离差异大
- 召回率可能更低
- **更接近真实数据**

**测试对比**:
```bash
# Uniform
./mlpstorage vectordb datagen --distribution uniform ...
./mlpstorage vectordb run ...
# Recall: 0.96, p99 latency: 20ms

# Normal
./mlpstorage vectordb datagen --distribution normal ...
./mlpstorage vectordb run ...
# Recall: 0.92, p99 latency: 25ms
```

**Why**:
1. **真实数据通常不是均匀分布** - embeddings 有聚类特征
2. **分布影响索引效率** - HNSW/DiskANN 对聚类数据更友好
3. **召回率测试要用真实分布** - 避免过度乐观

**How to apply**:
- 基准测试用 `uniform`（标准化对比）
- 生产评估用 `normal` 或真实数据
- 如果有真实 embedding 数据，导入测试
- 关注 worst-case 召回率（p99）

---

## 9. 参数扫描（Sweep Mode）的最佳实践

### Sweep 的价值

**手动测试**:
```bash
# 需要运行 N 次
for ef in 50 100 150 200 250 300 400 500; do
  ./mlpstorage vectordb run --search-ef $ef ...
done
```

**Sweep 模式**:
```bash
# 一次运行，自动测试所有配置
./mlpstorage vectordb run --mode sweep ...
```

### 分析 Sweep 结果

**关键问题**:
1. **召回率下限是多少？** → 业务需求决定（通常 0.95）
2. **在满足下限的配置中，哪个延迟最低？** → 最佳配置
3. **膝点在哪里？** → 性价比最高的点
4. **延迟和召回率的增长率？** → 预测更大规模的表现

**可视化分析**:
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('combined_bench_*.sweep.csv')

# 多维度对比
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. Latency vs Recall
axes[0, 0].plot(df['mean_recall'], df['mean_latency_ms'], 'o-')
axes[0, 0].set_xlabel('Recall')
axes[0, 0].set_ylabel('Latency (ms)')
axes[0, 0].axvline(x=0.95, color='r', linestyle='--')

# 2. QPS vs Recall
axes[0, 1].plot(df['mean_recall'], df['throughput_qps'], 'o-')
axes[0, 1].set_xlabel('Recall')
axes[0, 1].set_ylabel('QPS')

# 3. Latency vs search_ef
axes[1, 0].plot(df['search_ef'], df['mean_latency_ms'], 'o-')
axes[1, 0].set_xlabel('search_ef')
axes[1, 0].set_ylabel('Latency (ms)')

# 4. Recall vs search_ef
axes[1, 1].plot(df['search_ef'], df['mean_recall'], 'o-')
axes[1, 1].set_xlabel('search_ef')
axes[1, 1].set_ylabel('Recall')
axes[1, 1].axhline(y=0.95, color='r', linestyle='--')

plt.tight_layout()
plt.show()
```

**Why**:
1. **自动化节省时间** - 不需要手动运行多次
2. **结果更全面** - 覆盖更多配置点
3. **可视化帮助决策** - 曲线比表格更直观

**How to apply**:
- 首次调优时必须用 sweep 模式
- 定期重新 sweep（数据分布变化）
- 保存 sweep 结果用于报告和对比

---

## 10. 生产部署的考虑

### 从 Benchmark 到生产

**Benchmark 环境 vs 生产环境**:

| 维度 | Benchmark | 生产 |
|------|-----------|------|
| **数据量** | 固定（1M/10M） | 持续增长 |
| **查询模式** | 随机查询 | 有热点数据 |
| **并发度** | 固定 | 动态变化 |
| **故障处理** | 不考虑 | 需要容错 |

### 从 Benchmark 结果推导生产配置

**步骤**:
1. **确定目标**:
   - 目标 QPS：1000
   - 目标 p99 延迟：< 50ms
   - 最小召回率：> 0.95

2. **根据 Benchmark 结果推算**:
   ```
   Benchmark: 4 进程 → 400 QPS, p99=25ms, recall=0.96
   目标: 1000 QPS
   推算: 需要 10 进程
   考虑余量: 部署 12 进程
   ```

3. **验证假设**:
   - 实际部署 12 进程
   - 压测验证能否达到 1000 QPS
   - 监控 p99 延迟和召回率

4. **持续优化**:
   - 监控生产指标
   - 定期重新 benchmark
   - 根据数据增长调整配置

### 容量规划

**数据增长预测**:
```
当前: 1M 向量, p99=20ms
1年后: 10M 向量, p99=?

Benchmark 结果：
  1M → 10M: p99 增加 2×
预测: p99 ≈ 40ms

如果目标是 < 50ms → OK
如果目标是 < 30ms → 需要优化（更快 SSD/更多分片）
```

**Why**:
1. **Benchmark 是起点不是终点** - 生产环境更复杂
2. **需要留出余量** - 不能刚好达标
3. **持续监控很重要** - 数据增长会影响性能

**How to apply**:
- 定期重新 benchmark（每季度）
- 监控生产指标与 benchmark 的偏差
- 提前规划容量扩展
- 建立性能回归测试

---

## 核心结论

VectorDB Benchmark 提供了**向量数据库性能测试的标准化方法**。

关键 takeaway:
1. **召回率是核心指标** - 比延迟更重要（在某些场景）
2. **Ground Truth 必不可少** - FLAT 集合用于验证召回率
3. **索引算法要根据场景选择** - DiskANN/HNSW/AISAQ 各有优势
4. **Latency-Recall 曲线指导调优** - 找到最佳权衡点
5. **并发度有饱和点** - 不是越多越好
6. **磁盘 I/O 监控定位瓶颈** - 与 AI SSD Benchmark 协同
7. **数据分布影响性能** - 用真实分布测试
8. **Sweep 模式自动化调优** - 节省时间且结果全面
9. **从 Benchmark 到生产需要规划** - 考虑数据增长和容错
10. **持续监控和优化** - 定期重新 benchmark

这套方法论是 RAG 应用存储优化的重要基础。


## 相关概念

- [[ai-ssd]]
- [[nvme-ssd]]
