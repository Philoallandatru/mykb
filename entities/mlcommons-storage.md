---
type: entity
entity_type: tool
category: 基准测试
created: 2026-06-05
updated: 2026-06-05
tags:
  - entity
  - tool
  - benchmark
  - storage
  - mlperf
  - machine-learning
---

# MLCommons Storage Benchmark Suite

## 📋 基本信息

**类型**: 存储性能基准测试套件  
**类别**: ML 工作负载存储评估  
**开发者**: MLCommons  
**仓库**: https://github.com/mlcommons/storage  
**许可**: Apache-2.0  
**语言**: Python (91.9%), Shell (8.0%)

## 📝 描述

MLCommons Storage Benchmark Suite (MLPerf® Storage) 是一个全面的存储性能基准测试框架，专门用于表征支持机器学习工作负载的存储系统。提供标准化的方法来评估存储系统在真实 ML 场景下的性能。

### 核心价值

> **为机器学习工作负载提供标准化的存储性能基准测试，确保结果可比性和行业认可度**

---

## 🎯 四大核心工作负载

### 1. Training - 训练基准测试
**支持的模型**:
- FLUX.1 (文本到图像)
- RetinaNet (目标检测)
- DLRMv2 (推荐系统)

**测试重点**:
- 训练数据加载吞吐量
- 随机/顺序访问混合模式
- 分布式训练 I/O 协调

### 2. Checkpointing - 检查点
**模型规模**: Llama3 (8B ~ 1250B 参数)

**测试重点**:
- Checkpoint 保存速度 (write throughput)
- Checkpoint 加载速度 (read throughput)
- 大文件顺序写入性能
- 故障恢复时间

### 3. VectorDB - 向量数据库
**数据库**: Milvus VDB  
**索引算法**: DiskANN / HNSW / AiSAQ

**测试重点**:
- 向量插入吞吐量
- 相似度搜索延迟 (p50/p95/p99)
- 索引构建时间
- 混合读写 QoS

### 4. KVCache - LLM 上下文缓存
**测试重点**:
- KV cache 写入/读取速度
- 随机小块 I/O (64KB~256KB)
- 多用户并发访问
- Cache eviction 效率

---

## 🔧 技术特性

### 存储后端支持
- **File-based**: POSIX/并行文件系统 (NFS, Lustre, GPFS, WekaFS, BeeGFS)
- **Object-based**: S3 兼容对象存储 (AWS S3, MinIO, Ceph S3)

### 提交类型
- **CLOSED**: 严格限制更改，确保可比性
- **OPEN**: 允许灵活优化，鼓励创新

### 性能指标
- **吞吐量**: GB/s, IOPS
- **延迟**: p50/p95/p99
- **效率**: GB/s/RU (每机架单元), GB/s/KW (每千瓦)

### 技术架构
```
mlpstorage (主脚本)
  ├─ mlpstorage_py/ (核心代码)
  ├─ training/ (训练 workload)
  ├─ checkpointing/ (检查点 workload)
  ├─ vdb_benchmark/ (向量数据库 workload)
  └─ kv_cache_benchmark/ (KV cache workload)
```

---

## 💻 系统要求

### 环境
- **操作系统**: Ubuntu 24.04
- **Python**: 3.12.3
- **PyTorch**: CPU 版本（不需要 GPU）
- **包管理**: uv (快速依赖安装)

### 为什么不需要 GPU？
- 这是**存储性能**测试，不是模型训练
- 使用 CPU 版本 PyTorch 模拟 I/O 模式
- 集成 DLIO benchmark 进行 I/O 模式仿真
- 关注存储层，不关注计算层

---

## 🚀 使用示例

### 安装和设置
```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 设置环境
./setup_env.sh
uv sync
```

### 运行基准测试
```bash
# Training - FLUX.1
mlpstorage --workload training --model flux --file /mnt/storage/

# Checkpointing - Llama3 70B
mlpstorage --workload checkpointing --model llama3-70b --file /mnt/storage/

# VectorDB - Milvus with DiskANN
mlpstorage --workload vdb --index diskann --file /mnt/storage/

# KVCache - Mistral 7B
mlpstorage --workload kvcache --model mistral-7b --file /mnt/storage/
```

### 分布式执行
```bash
# MPI 多节点测试
mpirun -n 8 mlpstorage --workload training --model retinanet
```

---

## 🔗 相关笔记

### 概念
- [[kv-cache|KV 缓存]]
- [[ai-ssd|AI SSD]]
- [[gpu-direct-storage|GPU Direct Storage]]

### 相关工具
- [[lmcache|LMCache]] - 使用 SSD 作为 KV cache 存储
- [[vllm|vLLM]] - LLM 推理引擎

### 方法论
- [[kv-cache-benchmark-io-profiling|KV Cache Benchmark IO Profiling]] - 详细的 profiling 功能
- [[ai-ssd-benchmark-design|AI SSD Benchmark 设计]] - 可借鉴的方法论

### 原始文档
- [[.raw/mlcommons-storage-benchmark|MLCommons Storage 完整分析]]

---

## 💡 使用场景

### 适用情况
- **数据中心存储评估** - 评估 Lustre、GPFS、WekaFS 等并行文件系统
- **云存储评估** - 评估 S3、MinIO、Ceph 等对象存储
- **存储产品认证** - 获得 MLPerf 官方认证
- **性能调优** - 找到存储系统在 ML 场景下的瓶颈
- **采购决策** - 对比不同存储方案的性能

### 典型用户
- **云服务提供商** - AWS, Azure, GCP
- **HPC 中心** - 超算中心、研究机构
- **存储厂商** - VAST, WekaIO, DDN, NVIDIA
- **企业 AI 团队** - 需要评估内部存储基础设施

---

## 📊 与其他工具的对比

### vs FIO
| 维度 | MLCommons Storage | FIO |
|------|-------------------|-----|
| **定位** | ML 专用 benchmark | 通用 I/O benchmark |
| **I/O 模式** | 真实 ML workload | 人工 I/O pattern |
| **应用层开销** | 包含序列化、预处理 | 仅测原始 I/O |
| **标准化** | MLPerf 官方标准 | 事实标准 |
| **易用性** | 高（预设 workload） | 中（需手动配置） |

### vs AI SSD Benchmark
| 维度 | MLCommons Storage | AI SSD Benchmark |
|------|-------------------|------------------|
| **范围** | 通用存储系统 | AI PC 本地 SSD |
| **规模** | 数据中心级 | 单机 PC 级 |
| **场景** | 训练/检查点/VDB/KVCache | 模型加载/RAG/Recall/KVCache |
| **标准化** | MLPerf 官方 | 内部或厂商标准 |

**互补关系**:
- MLCommons Storage 提供了标准化方法论
- AI SSD Benchmark 可借鉴其 workload 设计
- KV cache 是两者共同关注的场景

---

## 🎓 集成工具

### DLIO Benchmark
**作用**: Deep Learning I/O Benchmark - 模拟深度学习 I/O 模式

**集成点**:
- Training workload 使用 DLIO 生成真实 I/O pattern
- 支持 TFRecord, HDF5, JPEG 等数据格式
- 模拟数据预处理和 augmentation

---

## 📈 性能规范化指标

### 机架单元效率
- **GB/s/RU**: 每机架单元的吞吐量
- **IOPs/RU**: 每机架单元的 IOPS

**Why**: 数据中心空间有限，需要考虑密度

### 功率效率
- **GB/s/KW**: 每千瓦的吞吐量
- **IOPs/KW**: 每千瓦的 IOPS

**Why**: 电力成本是数据中心的主要运营成本

---

## 💭 优势与局限

### 优势
- ✅ **MLPerf 官方认证** - 行业标准，结果权威
- ✅ **真实 workload** - 不是人工 I/O pattern
- ✅ **多场景覆盖** - 训练、检查点、VDB、KV cache
- ✅ **支持多种后端** - File 和 Object 存储
- ✅ **开源** - 代码公开，可自定义
- ✅ **活跃维护** - 持续更新

### 局限
- ⚠️ **数据中心导向** - 针对大规模系统，不适合 PC
- ⚠️ **环境要求高** - Ubuntu 24.04 + Python 3.12.3
- ⚠️ **学习曲线** - 需要理解 ML workload 特征
- ⚠️ **CPU only** - 不测试 GPU Direct Storage 场景
- ⚠️ **提交流程复杂** - 官方认证需要详细文档

---

## 📚 参考资料

### 官方资源
- [MLCommons Storage 仓库](https://github.com/mlcommons/storage)
- [MLPerf 官网](https://mlcommons.org/)
- [DLIO Benchmark](https://github.com/argonne-lcf/dlio_benchmark)

### 文档
- `docs/README.md` - 项目概述
- `tests/README.md` - 测试指南
- `Rules.md` - 提交规则
- `Submission_guidelines.md` - 提交指南

---

## 🔄 项目状态

- **提交数**: 404 次
- **主分支**: main
- **最近更新**: 持续活跃
- **社区**: MLCommons 社区支持

---

*创建于: 2026-06-05*  
*来源: MLCommons Storage GitHub 仓库分析*
