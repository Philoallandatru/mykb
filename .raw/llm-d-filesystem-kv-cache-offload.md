# llm-d Native KV Cache Offloading to File System

**来源**: https://llm-d.ai/blog/native-kv-cache-offloading-to-any-file-system-with-llm-d  
**发布**: llm-d team  
**类型**: 文件系统backend for KV cache storage

---

## 概述

llm-d的文件系统backend是一个**KV cache存储连接器**，基于vLLM的native Offloading Connector构建。

### 核心目标

1. 在并发和上下文长度增长时保持稳定吞吐量和低延迟
2. 显著扩大缓存空间
3. 在llm-d的多个副本和节点间实现KV重用

### 定位

> **"Storage is not intended to replace these mechanisms, but to complement them"**

存储offloading不是要替代GPU和CPU缓存，而是通过以下方式补充它们：
- 更大的可扩展性
- 更低的每GB成本
- 持久化KV存储

---

## 架构设计

### 关键特性

#### 1. 文件系统无关（File System Agnostic）

- 使用标准POSIX文件操作
- 支持任何标准文件系统
- 不依赖特定存储厂商

#### 2. 跨实例和节点的KV共享

```
vLLM Server 1
  ↓
Shared Storage Path
  ↑
vLLM Server 2
  ↑
vLLM Server N
```

多个vLLM服务器可通过访问相同共享路径重用缓存前缀。

#### 3. 持久化（Persistence）

KV数据可在以下情况中保存：
- Pod重启
- Pod重新调度
- 节点故障

#### 4. 企业存储集成

可利用具有以下特性的成熟存储系统：
- 持久性
- 监控
- 访问控制

---

## 性能设计选择

### 1. 完全异步I/O（Fully Asynchronous I/O）

通过vLLM的Offloading Connector实现：
- KV读写无需阻塞主路径
- 释放GPU周期用于prefill和decode操作

### 2. 高吞吐量并行化（High Throughput via Parallelism）

- 跨工作线程并行化I/O操作
- 提高带宽
- 减少尾延迟

### 3. 最小化对GPU计算的干扰

- 默认传输使用GPU DMA
- 不阻塞计算内核

---

## 支持的存储类型

已测试的存储选项包括：

| 存储类型 | 描述 |
|---------|------|
| **IBM Storage Scale** | 主要测试环境 |
| **本地存储** | 带文件系统挂载的NVMe驱动器 |
| **CephFS** | 分布式文件系统 |
| **通用** | 任何支持文件系统API或已挂载文件系统的存储 |

---

## 性能优化策略

### 优化技术

1. **工作线程池** - 实现I/O并行化
2. **GPU DMA** - 减少对计算内核的干扰
3. **异步设计** - 释放GPU周期用于prefill和decode操作
4. **可调参数**:
   - 存储块大小（以token为单位）
   - 工作线程数

---

## 使用方法

### 配置步骤

1. `pip install`
2. 提供存储目录路径
3. 可选调整参数：
   - 存储块大小
   - 工作线程数

### 详细文档

GitHub guide: `llm-d/guides/tiered-prefix-cache/storage/README.md`

---

## 性能测试结果

### Test 1: 单请求性能（Llama-3.1-70B, 4× H100）

**场景**: 长提示（long prompt）

**结果**:
- 相比prefill实现最高**16.8倍加速**
- GPU和CPU缓存在单请求场景下仍然更快
- 存储的价值在于**可扩展性**而非单个请求速度

**结论**: Storage offloading不是为了让单个请求更快，而是为了支持更多用户。

---

### Test 2: 可扩展性测试（多用户场景）

**问题场景**:
```
GPU内存只能支持少量用户提示
  ↓
CPU offloading延迟性能下降，但仍受容量限制
  ↓
工作集持续增长会导致性能崩溃
```

**Storage offloading解决方案**:
- 支持的KV缓存在工作集增长时保持吞吐量
- **"Prevents performance collapse when workloads outgrow GPU or CPU cache capacity"**

---

### Test 3: 真实工作负载（Llama-3.1-8B, 2× H100, 40 QPS）

**工作负载特征**:
```
2000 token系统提示
  +
256 token问题
  +
256 token解码
```

**操作混合**:
- KV加载
- Prefill
- Decode

**结果**:
- 随着用户数增长，存储offloading维持更好的整体吞吐量和TTFT
- 即使存储非顶级配置，异步使用仍实现更高吞吐量

---

### Test 4: 容量对比

**Llama-3.1-70B的一百万token需要305 GB KV cache**

**高端节点典型配置**:
- 8个GPU共2TB DRAM = 每GPU **250GB CPU内存**
- 约**80GB HBM per GPU**

**结论**: 
```
一百万token = 305 GB
  ↓
单GPU HBM (80GB) 不够
  ↓
单GPU CPU内存 (250GB) 勉强
  ↓
存储offloading提供无限扩展
```

---

## 与其他系统对比

### 现有方案

- LMCache
- NVIDIA Dynamo KVBM

### llm-d filesystem backend的优势

1. **简洁性** - 架构简单
2. **最小依赖** - 仅需llm-d和vLLM依赖
3. **性能改进** - 相比最先进的共享存储连接器表现出改进的性能

---

## 最佳实践

### 何时使用存储offloading

| 场景 | 是否使用Storage |
|------|----------------|
| 工作集超过GPU/CPU内存容量 | ✅ 是 |
| 需要跨副本共享KV数据 | ✅ 是 |
| 需要持久化缓存数据（重启、故障恢复） | ✅ 是 |
| 用户并发量和上下文长度持续增长 | ✅ 是 |
| 单请求低延迟优先 | ❌ 否（用GPU/CPU） |
| 工作集小于GPU内存 | ❌ 否（用GPU） |

---

## 设计考虑

### 1. 存储性能是关键

- 存储性能直接影响高吞吐KV cache命中
- 推荐使用高性能共享存储（NVMe, high-performance NAS）

### 2. 与其他机制结合使用

```
GPU缓存（最快，容量小）
  ↓
CPU缓存（快，容量中等）
  ↓
Storage offload（可扩展，持久化）
  +
智能路由（cache-aware scheduling）
```

应与CPU offloading和智能路由结合使用，而非替代。

### 3. 异步I/O设计

- 确保不阻塞GPU计算
- 允许GPU和I/O并行执行
- 最大化硬件利用率

---

## 后续功能路线图

### 计划中的功能

| 功能 | 描述 |
|------|------|
| **分层存储offload** | 作为CPU DRAM的第二层 |
| **NIXL backend集成** | 使用NVIDIA的低延迟传输库 |
| **对象存储offload** | 支持S3等对象存储 |
| **GPU Direct Storage (GDS)** | 直接GPU↔SSD路径，减少CPU bounce |

---

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                  llm-d Cluster                          │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ vLLM #1  │  │ vLLM #2  │  │ vLLM #N  │             │
│  │ (Replica)│  │ (Replica)│  │ (Replica)│             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │                    │
│       └─────────────┼─────────────┘                    │
│                     │                                  │
│         ┌───────────▼────────────┐                     │
│         │  Shared Storage Path   │                     │
│         │  (KV Cache Files)      │                     │
│         └───────────┬────────────┘                     │
└─────────────────────┼──────────────────────────────────┘
                      │
          ┌───────────▼────────────┐
          │   Storage Backend       │
          │  (IBM Storage Scale /   │
          │   CephFS / NVMe / ...)  │
          └─────────────────────────┘
```

---

## 性能数据总结

| 测试场景 | 配置 | 关键指标 |
|---------|------|---------|
| 单请求 | Llama-3.1-70B, 4×H100 | 16.8× prefill加速 |
| 多用户 | Llama-3.1-8B, 2×H100, 40 QPS | 防止性能崩溃 |
| 容量 | Llama-3.1-70B | 305 GB / 1M tokens |

---

## 核心价值陈述

**llm-d filesystem backend的三大价值**:

1. **可扩展性** - 突破GPU/CPU内存容量限制
2. **共享性** - 跨副本和节点的KV重用
3. **持久性** - 在故障和重启中保存KV数据

**一句话总结**:
> **llm-d filesystem backend通过将KV cache offload到共享存储，在用户并发和上下文长度持续增长时防止性能崩溃，并实现跨副本的KV重用和持久化。**

---

## 相关概念

- [[llm-d]] - llm-d分布式推理平台
- [[kv-cache]] - KV cache核心概念
- [[vllm]] - vLLM推理框架
- [[lmcache]] - LMCache KV cache middleware
- [[ai-ssd]] - AI SSD核心定义
- [[inference-frameworks-offload-mechanisms]] - 推理框架offload机制

---

**标签**: #llm-d #kv-cache #offload #filesystem #shared-storage #kubernetes #vllm
