# MLCommons Storage - VectorDB Benchmark

**来源**: https://github.com/mlcommons/storage/blob/main/vdb_benchmark/README.md  
**目的**: 评估和对比向量数据库在机器学习工作负载下的性能  
**状态**: Preview（预览阶段，仅支持OPEN类别提交）

---

## 概述

VectorDB Benchmark 是 MLCommons Storage Benchmark Suite 的四大工作负载之一，专门用于测试向量数据库在 RAG（检索增强生成）和语义搜索场景下的性能。

### 核心价值

> **提供标准化的向量数据库性能测试方法，评估向量插入、索引构建、相似度检索的端到端性能**

---

## 支持的数据库和索引算法

### 向量数据库
- **Milvus**: 当前唯一支持的向量数据库（开源、云原生）
- 未来可能支持：Pinecone, Weaviate, Qdrant 等

### 索引算法

| 算法 | 类型 | 特点 | 适用场景 |
|------|------|------|---------|
| **DiskANN** | 基于磁盘的ANN | 低内存占用，支持大规模数据 | 数据量大于内存 |
| **HNSW** | 基于内存的图索引 | 高召回率，快速检索 | 数据适合内存 |
| **AISAQ** | AI优化的标量量化 | 压缩存储，平衡性能 | 存储成本敏感 |
| **IVF Flat/PQ** | 倒排索引 | 基础实现，参考基线 | 对比测试 |

---

## 工作负载描述

### 数据集特征

**向量规模**:
- 小规模测试：500,000 向量（快速验证）
- 默认配置：1,000,000 向量
- 大规模测试：10,000,000 向量

**向量维度**:
- 默认：1536 维（OpenAI embedding 维度）
- 可配置：支持任意维度

**数据分布**:
- `uniform`: 均匀分布（默认）
- `normal`: 正态分布（模拟真实数据）

**数据类型**:
- `FLOAT_VECTOR`: 32位浮点向量

### 操作类型

**1. 向量加载（Load Phase）**
```
批量插入向量 → 创建索引 → 数据压缩（Compaction）
```

**关键参数**:
- `batch-size`: 批处理大小（影响插入吞吐量）
- `num-shards`: 分片数量（影响并行度）

**2. 向量检索（Query Phase）**
```
发起 top-k 相似度查询 → 返回最近邻向量 → 计算召回率
```

**关键参数**:
- `search-limit`: top-k 的 k 值（默认10）
- `search-ef`: HNSW 的 ef 参数或 DiskANN 的 search_list
- `processes`: 并发查询进程数

**3. 数据压缩（Compaction）**
```
合并数据段 → 优化存储布局 → 提高查询性能
```

---

## 性能指标定义

### 延迟指标（Latency）

**测量单位**: 毫秒（ms）

| 指标 | 含义 | 重要性 |
|------|------|--------|
| `mean_latency_ms` | 平均延迟 | 整体性能参考 |
| `median_latency_ms` | 中位数延迟 | 典型查询体验 |
| `p95_latency_ms` | 95百分位延迟 | 大部分用户体验 |
| `p99_latency_ms` | 99百分位延迟 | **关键SLA指标** |
| `p999_latency_ms` | 99.9百分位延迟 | 极端情况 |
| `p9999_latency_ms` | 99.99百分位延迟 | 长尾延迟 |

**Why p99 重要**: RAG 应用中，单个慢查询会拖慢整个响应

### 吞吐量指标（Throughput）

**`throughput_qps`**: 每秒查询数（Queries Per Second）

**计算方式**:
```
QPS = 总查询数 / 测试时长
```

**权衡**:
- 高并发 → 高 QPS，但可能增加延迟
- 低并发 → 低 QPS，但延迟稳定

### 召回率指标（Recall）

**定义**: 检索到的真实最近邻的比例

**计算方式**:
```
Recall@k = (ANN结果与精确结果的交集) / k
```

**测试流程**:
1. 使用 **FLAT 索引**创建 ground truth 集合（精确最近邻）
2. 基准测试期间收集 ANN（近似最近邻）搜索结果
3. 测试完成后计算 recall@k 统计数据

**召回率指标**:
- `mean_recall`: 平均召回率
- `median_recall`: 中位数召回率
- `min_recall` / `max_recall`: 最小/最大召回率
- `p95_recall` / `p99_recall`: 95/99百分位召回率

**Why 召回率重要**: 
- 召回率 < 0.9 → 用户会收到不相关的结果
- 召回率 > 0.95 → 通常可接受
- RAG 应用需要平衡召回率和延迟

### 磁盘 I/O 指标

**吞吐量指标**:
- `disk_read_mbps`: 磁盘读取速度（MB/s）
- `disk_write_mbps`: 磁盘写入速度（MB/s）

**IOPS 指标**:
- `disk_read_iops`: 读取 IOPS
- `disk_write_iops`: 写入 IOPS

**用途**:
- 识别存储瓶颈
- 评估索引算法的 I/O 模式
- 对比不同存储后端的性能

---

## 配置参数详解

### 数据库连接参数

```bash
--host 127.0.0.1        # Milvus 服务器地址
--port 19530            # Milvus 端口（默认19530）
```

### 数据集参数

```bash
--num-vectors 10000000  # 向量总数
--dimension 1536        # 向量维度
--num-shards 10         # 分片数量（影响并行度和分布）
--distribution uniform  # 数据分布（uniform/normal）
--batch-size 10000      # 批量插入大小
```

**优化建议**:
- `num-shards` 通常设置为 CPU 核心数或存储并行度
- `batch-size` 太小影响插入效率，太大占用内存

### 索引参数

```bash
--index-type DISKANN    # 索引类型（DISKANN/HNSW/AISAQ）
--metric-type COSINE    # 距离度量（COSINE/L2/IP）
--search-ef 200         # HNSW的ef或DiskANN的search_list
```

**索引选择**:
- **DiskANN**: 数据量 > 内存，关注存储成本
- **HNSW**: 数据量 < 内存，关注查询速度
- **AISAQ**: 平衡存储和性能

### 基准测试参数

```bash
--runtime 120                # 运行时长（秒）
--queries 100000             # 查询总数（query_count模式）
--num-query-processes 4      # 并发查询进程数
--search-limit 10            # top-k 的 k 值
--mode timed                 # 模式（timed/query_count/sweep）
--results-dir /tmp/vdb_results  # 结果输出目录
```

**模式说明**:
- **timed**: 运行指定时长，测量吞吐量
- **query_count**: 执行指定查询数，测量总时间
- **sweep**: 参数扫描，测试不同配置

---

## 使用流程

### Step 0: 估算存储需求（可选但推荐）

```bash
./mlpstorage vectordb datasize \
    --dimension 1536 \
    --num-vectors 10000000 \
    --index-type DISKANN \
    --num-shards 10
```

**输出示例**:
```
Raw data: 57.22 GB
DISKANN index: ~85 GB
Total estimated: 142 GB
```

**Why**: 避免测试中途因存储不足而失败

---

### Step 1: 加载向量数据

```bash
./mlpstorage vectordb datagen \
    --host 127.0.0.1 \
    --port 19530 \
    --config default \
    --force \
    --results-dir /tmp/vdb_results
```

**参数说明**:
- `--config default`: 使用预定义配置（1M向量，1536维）
- `--force`: 强制重新创建集合（删除已有数据）
- `--auto-create-flat`: 自动创建 FLAT 索引用于召回率计算

**配置文件位置**:
```
configs/vectordb/default.yaml
configs/vectordb/large.yaml      # 10M向量
configs/vectordb/small.yaml      # 500K向量（快速测试）
```

**过程**:
1. 连接 Milvus
2. 创建集合（Collection）
3. 批量插入向量
4. 创建索引（DiskANN/HNSW/AISAQ）
5. 数据压缩（Compaction）
6. 创建 FLAT 集合（ground truth）

---

### Step 2: 运行基准测试

#### 模式 1: 定时测试（Timed Mode）

```bash
./mlpstorage vectordb run \
    --host 127.0.0.1 \
    --port 19530 \
    --config default \
    --num-query-processes 4 \
    --runtime 120 \
    --results-dir /tmp/vdb_results
```

**用途**: 测量给定时间内的吞吐量和延迟

#### 模式 2: 查询计数（Query Count Mode）

```bash
./mlpstorage vectordb run \
    --host 127.0.0.1 \
    --port 19530 \
    --config default \
    --mode query_count \
    --queries 100000 \
    --results-dir /tmp/vdb_results
```

**用途**: 执行固定数量查询，测量总时间

#### 模式 3: 参数扫描（Sweep Mode）

```bash
./mlpstorage vectordb run \
    --host 127.0.0.1 \
    --port 19530 \
    --config default \
    --mode sweep \
    --runtime 120 \
    --results-dir /tmp/vdb_results
```

**用途**: 自动测试多个 `search-ef` 值，找到最佳配置

**扫描范围示例**（HNSW）:
```python
search_ef_values = [50, 100, 150, 200, 250, 300, 400, 500]
```

---

## 输出结果格式

### Runtime/Query_Count 模式输出

```
<output-dir>/
├── config.json                      # 运行配置快照
├── milvus_benchmark_p0.csv          # 进程0的时序数据
├── milvus_benchmark_p1.csv          # 进程1的时序数据
├── ...
├── recall_hits_p0.jsonl             # 进程0的召回结果
├── recall_hits_p1.jsonl             # 进程1的召回结果
├── ...
├── recall_stats.json                # 召回率统计
└── statistics.json                  # 聚合统计（延迟+召回+磁盘I/O）
```

**`statistics.json` 内容示例**:
```json
{
  "latency": {
    "mean_latency_ms": 12.5,
    "median_latency_ms": 11.2,
    "p95_latency_ms": 18.3,
    "p99_latency_ms": 24.7,
    "p999_latency_ms": 45.2
  },
  "throughput": {
    "throughput_qps": 320.5
  },
  "recall": {
    "mean_recall": 0.952,
    "median_recall": 0.960,
    "p95_recall": 0.930,
    "p99_recall": 0.910
  },
  "disk_io": {
    "disk_read_mbps": 234.5,
    "disk_write_mbps": 12.3,
    "disk_read_iops": 4521,
    "disk_write_iops": 89
  }
}
```

### Sweep 模式输出

```
results/
├── combined_bench_<tag>_<ts>.json          # 所有运行的详细结果
├── combined_bench_<tag>_<ts>.csv           # 每次运行的表格摘要
└── combined_bench_<tag>_<ts>.sweep.csv     # 参数扫描详情
```

**`sweep.csv` 示例**:
```csv
search_ef,mean_latency_ms,p99_latency_ms,throughput_qps,mean_recall
50,8.5,15.2,450.2,0.850
100,11.2,20.1,380.5,0.920
200,15.8,28.5,290.3,0.960
400,24.3,42.1,180.7,0.980
```

**用途**: 绘制 latency-recall 曲线，找到最佳权衡点

---

## 召回率计算机制

### Ground Truth 集合（FLAT索引）

**为什么需要 FLAT**:
- FLAT 是精确最近邻（Exact NN）
- 不做任何近似，结果100%准确
- 作为 ANN 算法的基准

**创建方式**:
```bash
# 自动创建（推荐）
./mlpstorage vectordb datagen \
    --auto-create-flat \
    ...

# 手动创建
# 在配置文件中设置 flat_gt_collection_name
```

### 召回率计算流程

1. **测试期间**:
   - 每个查询记录 ANN 返回的 top-k 向量 ID
   - 同时查询 FLAT 集合获取精确 top-k

2. **测试完成后**:
   - 对比 ANN 和 FLAT 的结果
   - 计算交集大小
   - Recall@k = |ANN ∩ FLAT| / k

3. **聚合统计**:
   - 计算所有查询的平均召回率
   - 计算 p95/p99 召回率（worst-case）

### 召回率验证

**如果召回率显示 0.000**:
```bash
# 检查 FLAT 集合是否存在
# 使用 Milvus 客户端或 Web UI 确认
# 确保 datagen 时使用了 --auto-create-flat
```

**如果召回率偏低（< 0.9）**:
- 增加 `search-ef` 值（HNSW/DiskANN）
- 调整索引构建参数
- 检查数据分布是否适合当前索引

---

## 最佳实践

### 1. 维度一致性

**规则**: 
> "vector dimension must be consistent between data loading and benchmarking"

**Why**: Milvus 会拒绝维度不匹配的查询

**How**:
- 在 `datagen` 和 `run` 中使用相同的 `--config`
- 或确保 `--dimension` 参数一致

### 2. 快速验证

**策略**: 使用小数据集快速验证配置

```bash
# 使用 small 配置（500K向量）
./mlpstorage vectordb datagen --config small ...
./mlpstorage vectordb run --config small ...
```

**用途**:
- 验证 Milvus 连接
- 验证配置正确性
- 快速迭代参数

### 3. 存储规划

**策略**: 测试前估算存储需求

```bash
./mlpstorage vectordb datasize \
    --dimension 1536 \
    --num-vectors 10000000 \
    --index-type DISKANN
```

**Why**: 避免测试中途存储不足

### 4. 参数扫描找最佳配置

**策略**: 使用 sweep 模式自动测试多个配置

```bash
./mlpstorage vectordb run \
    --mode sweep \
    --runtime 60 \
    ...
```

**分析**:
```python
import pandas as pd
df = pd.read_csv('combined_bench_*.sweep.csv')

# 绘制 latency-recall 曲线
import matplotlib.pyplot as plt
plt.plot(df['mean_recall'], df['mean_latency_ms'])
plt.xlabel('Recall')
plt.ylabel('Latency (ms)')
plt.show()

# 找到召回率 > 0.95 且延迟最低的配置
best = df[df['mean_recall'] > 0.95].nsmallest(1, 'mean_latency_ms')
print(f"Best search_ef: {best['search_ef'].values[0]}")
```

### 5. 召回率验证

**策略**: 首次运行时启用 FLAT ground truth

```bash
./mlpstorage vectordb datagen \
    --auto-create-flat \
    ...
```

**验证**:
```bash
# 检查 recall_stats.json
cat /tmp/vdb_results/recall_stats.json | jq '.mean_recall'
```

### 6. 并发调优

**策略**: 测试不同并发度找到最佳 QPS

```bash
# 测试 1/2/4/8/16 进程
for p in 1 2 4 8 16; do
  ./mlpstorage vectordb run \
    --num-query-processes $p \
    --runtime 60 \
    --results-dir /tmp/vdb_p$p
done
```

**分析**: 找到 QPS 饱和点（增加进程不再提升 QPS）

---

## 典型使用场景

### 场景 1: 对比不同索引算法

```bash
# 测试 DiskANN
./mlpstorage vectordb datagen --index-type DISKANN ...
./mlpstorage vectordb run ...

# 测试 HNSW
./mlpstorage vectordb datagen --index-type HNSW ...
./mlpstorage vectordb run ...

# 测试 AISAQ
./mlpstorage vectordb datagen --index-type AISAQ ...
./mlpstorage vectordb run ...
```

**对比维度**:
- 延迟（p99）
- 吞吐量（QPS）
- 召回率
- 磁盘空间占用
- 索引构建时间

### 场景 2: 评估存储后端

**目标**: 对比 NVMe SSD vs S3 对象存储

```bash
# NVMe 本地存储
# Milvus 配置 data_dir = /mnt/nvme/milvus
./mlpstorage vectordb run ...

# S3 对象存储
# Milvus 配置 data_dir = s3://bucket/milvus
./mlpstorage vectordb run ...
```

**关注指标**:
- `disk_read_mbps` / `disk_read_iops`
- `p99_latency_ms`

### 场景 3: 容量规划

**目标**: 确定单节点可以支持的最大向量数

```bash
# 逐步增加数据量
for n in 1000000 5000000 10000000 20000000; do
  ./mlpstorage vectordb datagen --num-vectors $n ...
  ./mlpstorage vectordb run ...
done
```

**观察**:
- 延迟是否线性增长
- QPS 是否下降
- 磁盘 I/O 是否饱和

---

## 与 AI SSD Benchmark 的关联

### 共同场景：RAG 应用

**VectorDB Benchmark**:
- 测试向量数据库的端到端性能
- 包含向量插入、索引构建、检索全流程
- 关注应用层性能（延迟、召回率、QPS）

**AI SSD Benchmark - AI-RAG-Build / AI-RAG-Query**:
- 测试 SSD 在 RAG 场景的性能
- 关注存储层性能（I/O 延迟、吞吐量）
- 使用 fio 或真实 RAG 框架

**互补关系**:
```
VectorDB Benchmark (应用层)
  ↓ 依赖
Storage Performance (存储层)
  ↓ 测试
AI SSD Benchmark (存储优化)
```

### 性能瓶颈定位

**流程**:
1. 运行 VectorDB Benchmark，发现 p99 延迟高
2. 查看 `disk_read_iops` 和 `disk_read_mbps`
3. 如果磁盘 I/O 饱和 → SSD 是瓶颈
4. 运行 AI SSD Benchmark 验证 SSD 性能
5. 优化 SSD（选择更快的 SSD 或调整配置）

---

## 相关概念

- [[mlcommons-storage]] - MLCommons Storage 整体介绍
- [[kv-cache-benchmark-io-profiling]] - KV Cache benchmark 的 profiling 功能
- [[ai-ssd-benchmark-design]] - AI SSD benchmark 设计方法论
- [[ai-ssd]] - AI SSD 的核心定义

---

**总结**: VectorDB Benchmark 提供了标准化的向量数据库性能测试方法，覆盖数据加载、索引构建、相似度检索的全流程。支持 DiskANN/HNSW/AISAQ 等主流索引算法，提供延迟、吞吐量、召回率、磁盘 I/O 等多维度指标，是评估 RAG 应用存储性能的重要工具。
