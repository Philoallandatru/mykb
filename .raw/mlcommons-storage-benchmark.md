# MLCommons Storage Benchmark Suite

**仓库**: https://github.com/Philoallandatru/storage (fork from mlcommons/storage)  
**描述**: MLPerf® Storage Benchmark Suite - 用于评估支持机器学习工作负载的存储系统性能的基准测试套件  
**许可**: Apache-2.0  
**语言**: Python (91.9%), Shell (8.0%)

---

## 项目概述

MLCommons Storage Benchmark Suite 是一个全面的存储性能基准测试框架，专门用于表征支持 ML 工作负载的存储系统。该项目提供了标准化的方法来评估存储系统在真实机器学习场景下的性能。

### 核心价值

> **为机器学习工作负载提供标准化的存储性能基准测试，涵盖训练、检查点、向量数据库和 KV 缓存四大场景**

---

## 四大核心工作负载

### 1. Training - 训练基准测试

**支持的模型**:
- **FLUX.1**: 文本到图像生成模型
- **RetinaNet**: 目标检测模型
- **DLRMv2**: 推荐系统模型

**测试重点**:
- 训练数据加载性能
- 大规模数据集读取吞吐量
- 随机访问和顺序访问混合模式
- 分布式训练的 I/O 协调

---

### 2. Checkpointing - LLM 检查点

**模型规模**:
- Llama3: 8B ~ 1250B 参数
- 覆盖从小型到超大型 LLM

**测试重点**:
- 检查点保存速度（write throughput）
- 检查点加载速度（read throughput）
- 大文件顺序写入性能
- 故障恢复时间（checkpoint load time）

**典型场景**:
```
训练过程中周期性保存：
  每 N 步保存一次 checkpoint (几十 GB 到数 TB)
  
故障恢复：
  从最近的 checkpoint 快速恢复训练
```

---

### 3. VectorDB - 向量数据库基准测试

**数据库引擎**:
- **Milvus VDB**: 开源向量数据库

**索引算法**:
- **DiskANN**: 基于磁盘的近似最近邻搜索
- **HNSW**: 层次化可导航小世界图
- **AiSAQ**: AI 优化的标量量化

**测试重点**:
- 向量插入吞吐量
- 相似度搜索延迟（p50/p95/p99）
- 索引构建时间
- 混合读写负载下的 QoS
- 大规模向量数据的存储效率

**典型场景**:
```
RAG (Retrieval-Augmented Generation):
  向量库构建 → 索引 → 相似度检索 → 返回 top-k 结果
```

---

### 4. KVCache - LLM 上下文缓存

**测试重点**:
- KV cache 写入速度（prefill phase）
- KV cache 读取延迟（decode phase）
- 随机小块 I/O 性能（64KB ~ 256KB）
- 多用户并发访问
- Cache eviction 策略效率

**典型场景**:
```
长上下文 LLM 推理：
  GPU 内存不足 → 部分 KV cache 卸载到存储
  Prefill: 写入 KV cache 到存储
  Decode: 从存储读取 KV cache
```

**关联**: 这个 benchmark 就是我们之前分析的 [[kv-cache-benchmark-io-profiling|KV Cache Benchmark]]

---

## 存储后端支持

### File-based (POSIX)
```bash
--file /mnt/storage/
```

**支持的文件系统**:
- NFS
- Lustre
- GPFS
- WekaFS
- BeeGFS
- 本地文件系统

### Object-based (S3)
```bash
--object s3://bucket-name/
```

**支持的对象存储**:
- AWS S3
- MinIO
- Ceph S3
- 其他 S3 兼容存储

---

## 提交类型

### CLOSED 提交

**规则**:
- 严格限制更改
- 只能修改特定配置参数
- 确保结果可比性
- 适合标准化对比

**目标**: 公平对比不同存储系统的性能

### OPEN 提交

**规则**:
- 允许灵活调整和优化
- 可以修改代码、算法、配置
- 鼓励创新优化
- 需要详细说明所做的更改

**目标**: 探索存储系统的最大潜力

---

## 性能规范化指标

### 机架单元效率
- **GB/s/RU**: 每机架单元的吞吐量
- **IOPs/RU**: 每机架单元的 IOPS

### 功率效率
- **GB/s/KW**: 每千瓦的吞吐量
- **IOPs/KW**: 每千瓦的 IOPS

**Why**: 数据中心需要考虑空间和能耗成本，不只是原始性能

---

## 技术架构

### 核心组件

```
mlpstorage (主脚本)
  ├─ mlpstorage_py/ (核心代码)
  │   ├─ workload handlers
  │   ├─ storage backends
  │   ├─ metrics collection
  │   └─ result aggregation
  │
  ├─ training/ (训练 workload)
  ├─ checkpointing/ (检查点 workload)
  ├─ vdb_benchmark/ (向量数据库 workload)
  └─ kv_cache_benchmark/ (KV cache workload)
```

### 依赖管理

**使用 uv 包管理器**:
```bash
# 快速安装依赖
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

**优势**:
- 比 pip 快 10-100×
- 自动解决依赖冲突
- 锁定文件保证可重复性

### 分布式执行

**MPI 支持**:
```bash
mpirun -n 8 mlpstorage --workload training --model retinanet
```

**用途**:
- 多节点协调测试
- 模拟分布式训练场景
- 测试存储系统的并发性能

---

## 系统要求

### 环境
- **操作系统**: Ubuntu 24.04
- **Python**: 3.12.3
- **PyTorch**: CPU 版本（不需要 GPU）

### 硬件
- **CPU**: 根据 workload 不同
- **内存**: 根据 workload 不同
- **存储**: 被测试的存储系统

### 为什么不需要 GPU？
- 这是**存储性能**基准测试，不是模型训练
- 使用 CPU 版本 PyTorch 模拟 I/O 模式
- 关注存储吞吐量和延迟，不关注计算性能
- 集成 DLIO benchmark 进行 I/O 模式仿真

---

## 主要目录结构

```
storage/
├── mlpstorage                    # 主要基准测试脚本
├── mlpstorage.yaml               # MLPerf 存储配置
├── system_configuration.yaml     # 系统描述模板
├── setup_env.sh                  # 环境设置脚本
│
├── docs/                         # 文档
│   ├── README.md                 # 项目概述
│   └── ...
│
├── mlpstorage_py/                # Python 核心代码
│   ├── workload handlers
│   ├── storage backends
│   └── metrics collection
│
├── training/                     # 训练基准测试
├── checkpointing/                # 检查点基准测试
├── vdb_benchmark/                # 向量数据库基准测试
├── kv_cache_benchmark/           # KV 缓存基准测试
│
├── configs/                      # 配置文件
├── ansible/                      # 自动化部署
├── tests/                        # 测试代码
│
├── Rules.md                      # 提交规则
├── Submission_guidelines.md      # 提交指南
├── DEVELOPMENT.md                # 开发文档
└── CODE_IMPROVEMENT_PLAN.md      # 代码改进计划
```

---

## 集成工具

### DLIO Benchmark

**作用**: Deep Learning I/O Benchmark - 模拟深度学习的 I/O 模式

**集成点**:
- Training workload 使用 DLIO 生成真实的 I/O pattern
- 支持各种数据格式（TFRecord, HDF5, JPEG, etc.）
- 模拟数据预处理和 augmentation 的 I/O 开销

---

## 使用示例

### 运行 Training Benchmark
```bash
# FLUX.1 模型训练
mlpstorage --workload training --model flux --file /mnt/storage/

# RetinaNet 模型训练
mlpstorage --workload training --model retinanet --object s3://bucket/
```

### 运行 Checkpointing Benchmark
```bash
# Llama3 8B checkpoint
mlpstorage --workload checkpointing --model llama3-8b --file /mnt/storage/

# Llama3 70B checkpoint
mlpstorage --workload checkpointing --model llama3-70b --file /mnt/storage/
```

### 运行 VectorDB Benchmark
```bash
# Milvus with DiskANN
mlpstorage --workload vdb --index diskann --file /mnt/storage/

# Milvus with HNSW
mlpstorage --workload vdb --index hnsw --object s3://bucket/
```

### 运行 KVCache Benchmark
```bash
# KV cache benchmark
mlpstorage --workload kvcache --model mistral-7b --file /mnt/storage/
```

---

## 与其他工作的关联

### 与 FIO 的区别

**FIO**:
- 通用存储性能测试工具
- 测试原始 I/O 性能（顺序读写、随机读写）
- 不模拟真实应用的 I/O 模式

**MLCommons Storage**:
- 专门针对 ML 工作负载
- 模拟真实应用的 I/O 模式
- 包含应用层的开销（序列化、反序列化、数据预处理）

### 与 AI SSD Benchmark 的关系

[[ai-ssd-benchmark-design|AI SSD Benchmark]] 可以看作是 MLCommons Storage 的简化版或补充：

| 维度 | MLCommons Storage | AI SSD Benchmark |
|------|-------------------|------------------|
| **范围** | 通用存储系统 | 专门针对 AI PC SSD |
| **场景** | 训练、检查点、VDB、KV cache | 模型加载、RAG、Recall、KV cache、多模态 |
| **规模** | 数据中心级 | 单机 PC 级 |
| **标准化** | MLPerf 官方标准 | 内部或厂商标准 |
| **工具** | Python + DLIO | fio + 真实应用 |

**互补关系**:
- MLCommons Storage 提供了标准化的方法论
- AI SSD Benchmark 可以借鉴其 workload 设计思路
- KV cache benchmark 是两者共同关注的场景

---

## 最佳实践

### 运行基准测试前

1. **阅读文档**:
   - `docs/README.md`: 项目概述
   - `tests/README.md`: 测试指南
   - `Rules.md`: 提交规则
   - `Submission_guidelines.md`: 提交指南

2. **配置系统**:
   - 填写 `system_configuration.yaml`
   - 描述存储系统硬件配置
   - 记录网络拓扑和连接

3. **环境设置**:
   ```bash
   ./setup_env.sh
   uv sync
   ```

### 运行基准测试中

1. **选择合适的 workload**:
   - 根据实际使用场景选择
   - 可以运行多个 workload

2. **选择提交类型**:
   - CLOSED: 标准对比
   - OPEN: 性能优化

3. **监控系统**:
   - 监控 CPU、内存、网络、存储
   - 记录日志和错误

### 运行基准测试后

1. **分析结果**:
   - 查看输出的性能指标
   - 对比不同配置的结果

2. **准备提交**:
   - 按照 `Submission_guidelines.md` 准备材料
   - 包含系统配置、测试结果、日志

---

## 开发和贡献

### 开发文档
- `DEVELOPMENT.md`: 开发指南
- `CODE_IMPROVEMENT_PLAN.md`: 代码改进计划
- `CLAUDE.md`: Claude AI 相关文档（可能包含 AI 辅助开发的说明）

### 测试
```bash
# 运行单元测试
pytest tests/

# 运行集成测试
./run_integration_tests.sh
```

### 自动化部署
```bash
# 使用 Ansible 部署
cd ansible/
ansible-playbook deploy.yml
```

---

## 项目统计

- **提交数**: 404 次
- **主分支**: main
- **Fork 来源**: mlcommons/storage（官方 MLPerf Storage 项目）
- **活跃状态**: 持续更新中

---

## 参考资料

- **官方仓库**: https://github.com/mlcommons/storage
- **MLPerf 官网**: https://mlcommons.org/
- **DLIO Benchmark**: https://github.com/argonne-lcf/dlio_benchmark

---

## 相关概念

- [[kv-cache]] - KV cache 核心概念
- [[kv-cache-benchmark-io-profiling]] - KV cache benchmark 的 IO profiling 功能
- [[ai-ssd-benchmark-design]] - AI SSD benchmark 设计方法论
- [[lmcache]] - LMCache 使用 SSD 作为 KV cache 存储

---

**总结**: MLCommons Storage Benchmark Suite 提供了标准化的 ML 存储性能测试方法，覆盖训练、检查点、向量数据库和 KV 缓存四大场景。其 KV cache benchmark 与我们之前分析的工具是同一套系统，方法论可以迁移到 AI SSD Benchmark 设计中。
