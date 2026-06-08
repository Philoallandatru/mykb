---
aliases:
- pagedattention
tags:
- llm-inference
- memory-management
- vllm
- optimization
created: '2026-06-09'
---

# paged-attention

## 定义

PagedAttention 是 vLLM 提出的一种高效 KV cache 内存管理技术，将 KV cache 分割为固定大小的块（pages），存储在非连续的 GPU 内存空间中。

## 核心原理

### 传统方法的问题
- 为每个序列预分配连续内存
- 内存浪费率 60-80%（过度分配 + 内部碎片 + 外部碎片）
- 限制了可并发处理的序列数量

### PagedAttention 解决方案
- **分块存储**: 将 KV cache 分割为固定大小的块（如 16 个 token）
- **非连续内存**: 块可以存储在非连续的 GPU 内存位置
- **按需分配**: 仅在需要时分配新块
- **内存共享**: 多个序列可共享相同的 KV cache 块（用于 prefix caching）

## 性能提升

- **内存利用率**: < 4% 浪费 vs 60-80% 传统系统
- **吞吐量提升**: 相比 HuggingFace Transformers 提升 24 倍
- **相比 TGI**: 提升 3.5 倍
- **批次大小**: 可批处理更多序列，提高 GPU 利用率

## 实现细节

### 块管理
- 块大小通常为 16 或 32 个 token
- 使用块表（block table）跟踪每个序列的块
- 类似操作系统的虚拟内存分页机制

### 注意力计算
- 修改注意力计算以支持非连续内存访问
- 每个块独立计算，然后合并结果
- 对计算性能影响很小（< 5%）

## 应用场景

1. **高吞吐量服务**: 最大化批次大小
2. **长上下文推理**: 高效管理大量 KV cache
3. **Prefix caching**: 共享公共前缀的 KV cache
4. **多租户服务**: 灵活的内存分配

## 技术优势

- **接近最优的内存利用**: 浪费率 < 4%
- **灵活性**: 支持可变长度序列
- **可扩展性**: 易于扩展到分布式场景
- **兼容性**: 可与其他优化技术组合

## 与操作系统虚拟内存的类比

| 操作系统 | PagedAttention |
|---------|----------------|
| 虚拟内存页 | KV cache 块 |
| 页表 | 块表 |
| 页面置换 | 块回收策略 |
| 内存碎片管理 | 块级别管理 |

## 相关概念
- [[multi-query-attention]]

- [[kv-cache]]
- [[vllm]]
- [[continuous-batching]]
