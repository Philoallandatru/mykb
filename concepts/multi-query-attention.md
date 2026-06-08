---
aliases:
- mqa
- grouped-query-attention
- gqa
tags:
- attention
- memory-optimization
- llm-inference
created: '2026-06-09'
---

# multi-query-attention

## 定义

Multi-Query Attention (MQA) 是一种注意力机制变体，在多个注意力头之间共享键（keys）和值（values），而不是为每个头维护独立的副本。

## 核心原理

### 标准 Multi-Head Attention
- 每个头有独立的 Q、K、V 投影
- KV cache 大小: `num_heads × seq_len × head_dim`
- 内存占用随头数线性增长

### Multi-Query Attention
- 每个头有独立的 Q 投影
- 所有头共享同一组 K 和 V
- KV cache 大小: `1 × seq_len × head_dim`
- 内存占用不随头数增长

## 内存节省

### KV Cache 减少
假设模型配置：
- 32 个注意力头
- 128 的 head_dim
- 2048 的序列长度

**标准 MHA**:
- KV cache per layer: 32 × 2048 × 128 × 2 = 16 MB (FP16)

**MQA**:
- KV cache per layer: 1 × 2048 × 128 × 2 = 0.5 MB (FP16)
- **节省 32 倍内存**

### 对大模型的影响
- LLaMA-70B: KV cache 从数百 GB 降至数十 GB
- 支持更大的批次大小
- 降低内存带宽需求

## 性能权衡

### 优势
- **内存效率**: KV cache 大幅减少
- **推理加速**: 减少内存传输，提升吞吐量
- **批次大小**: 可处理更多并发请求

### 潜在劣势
- **表达能力**: 共享 K/V 可能略微降低模型能力
- **训练成本**: 需要从头训练或 fine-tuning

## 实践应用

### 模型采用
- **PaLM**: Google 的大模型使用 MQA
- **Falcon**: 40B/180B 使用 MQA
- **StarCoder**: 代码生成模型

### 推理优化
- 与 PagedAttention 结合
- 降低 KV cache offload 的开销
- 提升长上下文推理效率

## Grouped-Query Attention (GQA)

### 折中方案
- 将头分为若干组
- 每组共享 K/V
- 平衡表达能力和内存效率

### 配置示例
- 32 个查询头
- 8 组（每组 4 个头共享 K/V）
- KV cache 减少 4 倍

### 模型采用
- **LLaMA-2-70B**: 使用 GQA (8 groups)
- **Mistral-7B**: 使用 GQA

## 实现细节

### 前向计算
```python
# 标准 MHA
Q = Linear_Q(x)  # [batch, seq, num_heads, head_dim]
K = Linear_K(x)  # [batch, seq, num_heads, head_dim]
V = Linear_V(x)  # [batch, seq, num_heads, head_dim]

# MQA
Q = Linear_Q(x)  # [batch, seq, num_heads, head_dim]
K = Linear_K(x)  # [batch, seq, 1, head_dim]  # 单组
V = Linear_V(x)  # [batch, seq, 1, head_dim]  # 单组

# 广播 K, V 到所有头
K = K.expand(-1, -1, num_heads, -1)
V = V.expand(-1, -1, num_heads, -1)
```

## 与其他技术的关系

- **PagedAttention**: 减少需要管理的 KV cache 总量
- **KV Cache Quantization**: MQA + 量化进一步节省内存
- **Prefix Caching**: 共享前缀的效率更高

## 研究论文

- **Fast Transformer Decoding** (Shazeer, 2019) - 提出 MQA
- **GQA: Training Generalized Multi-Query Transformer** (Ainslie et al., 2023)


## 相关概念
- [[kv-cache-quantization]]

- [[kv-cache]]
- [[paged-attention]]
