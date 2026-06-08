---
type: concept
category: 系统架构
source: Tutti论文 (arXiv:2605.03375)
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - llm
  - caching
  - performance
---

# KV Cache (键值缓存)

## 💡 定义

KV Cache（Key-Value Cache）是大语言模型（LLM）推理中的一种优化技术，用于存储Transformer注意力机制中的键（Key）和值（Value）张量，避免重复计算。

## 📝 详细说明

### 工作原理

在自回归文本生成过程中：
- 每生成一个新token，都需要关注之前所有token的上下文
- 不使用缓存：每次都重新计算所有历史token的K和V → O(n²)复杂度
- 使用KV缓存：保存已计算的K/V，只计算新token → O(n)复杂度

### 内存需求

对于长上下文LLM：
- **每层**存储：`(batch_size × seq_length × hidden_dim × 2)` 的浮点数
- **多层模型**：总内存需求可达数十GB
- **问题**：GPU HBM容量有限（40-80GB），长上下文易爆内存

### 传统解决方案

1. **仅GPU内存** - 快速但容量受限
2. **CPU内存交换** - 容量大但PCIe带宽瓶颈
3. **SSD卸载** - 容量无限但I/O延迟高

## 🔗 相关概念

- [[Transformer-Attention|Transformer注意力机制]]
- [[GPU-Memory-Hierarchy|GPU内存层次结构]]
- [[Tutti-System|Tutti系统]] - 实用的SSD-backed KV缓存方案
- [[Memory-Offloading|内存卸载]]
- [[ai-ssd]] - AI SSD 针对 KV cache 场景做 64K~256K 随机读优化
- [[lmcache]] - LMCache 使用 SSD 作为 KV cache 的分布式存储层

## 💼 应用场景

### 长上下文场景
- **长对话历史** - 数小时的客服对话
- **文档分析** - 处理整本书籍或长报告
- **代码补全** - 大型代码库上下文
- **RAG系统** - 检索增强生成

### 优化权衡
- **小batch + 长序列** - KV缓存占主导
- **大batch + 短序列** - 激活内存占主导

## 📚 参考资料

- Tutti论文: [[tutti-paper-2605.03375|arXiv:2605.03375]]
- PagedAttention (vLLM的原始KV缓存管理)
- FlashAttention (注意力计算优化)

## 💭 关键挑战

1. **内存墙** - GPU内存不足以存储长上下文的KV缓存
2. **I/O瓶颈** - 从SSD/CPU内存恢复缓存的延迟
3. **碎片化** - GPU内存布局导致随机I/O
4. **调度复杂性** - 何时预取、何时驱逐

---

*创建于: 2026-06-04*
*来源: Tutti论文分析*


## 相关概念
- [[kv-cache-quantization]]
- [[multi-query-attention]]
- [[flash-attention]]
- [[flashinfer]]

- [[flashinfer-jit-cache]]
