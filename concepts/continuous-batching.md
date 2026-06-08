---
aliases:
- iteration-level-scheduling
- dynamic-batching
tags:
- llm-inference
- scheduling
- batching
- vllm
created: '2026-06-09'
---

# continuous-batching

## 定义

Continuous Batching（连续批处理）是一种动态批处理策略，在迭代级别（iteration-level）而非批次级别（batch-level）调度请求，实时处理到达的请求。

## 核心概念

### Static Batching 的问题
- 等待整个批次的所有序列完成才能处理新请求
- 短序列完成后，GPU 资源浪费在等待长序列
- 平均延迟高，资源利用率低

### Continuous Batching 的解决方案
- **迭代级调度**: 每次生成迭代后重新调度
- **动态插入**: 已完成序列的槽位立即分配给新请求
- **无等待**: 不等待整个批次完成

## 工作原理

### 调度流程
1. 批次中的序列并行生成 token
2. 某个序列完成（生成 EOS 或达到最大长度）
3. 立即从批次中移除该序列
4. 如果有等待的请求，立即插入到空出的槽位
5. 继续下一次迭代

### 与传统批处理对比

**Static Batching**:
```
Batch 1: [Seq A (50 tokens), Seq B (100 tokens), Seq C (80 tokens)]
→ 等待所有序列完成（100 次迭代）
Batch 2: [Seq D, Seq E, Seq F]
```

**Continuous Batching**:
```
Iter 1-50:  [Seq A, Seq B, Seq C]
Iter 51:    [Seq D, Seq B, Seq C]  # A 完成，D 插入
Iter 80:    [Seq D, Seq B, Seq E]  # C 完成，E 插入
Iter 100:   [Seq D, Seq F, Seq E]  # B 完成，F 插入
```

## 性能提升

- **吞吐量**: 相比 static batching 提升 23 倍
- **延迟**: 降低 p50 延迟
- **资源利用率**: GPU 始终保持满负载
- **响应性**: 新请求更快开始处理

## 实现要点

### 1. 高效的批次重组
- 每次迭代后快速更新批次成员
- 最小化重组开销（< 1ms）

### 2. KV Cache 管理
- 需要灵活的内存管理（如 PagedAttention）
- 支持动态分配和释放

### 3. 调度策略
- FCFS（先来先服务）
- 优先级队列
- 公平性保证

## 应用场景

1. **在线服务**: 处理实时到达的请求
2. **高吞吐量场景**: 最大化 GPU 利用率
3. **混合负载**: 长短序列混合
4. **低延迟要求**: 减少排队等待时间

## 与其他技术的关系

- **PagedAttention**: 提供灵活的内存管理基础
- **Dynamic Batching**: 传统动态批处理只在批次级别调度
- **Speculative Decoding**: 可以结合使用

## 实现挑战

1. **批次大小波动**: 需要处理批次大小的快速变化
2. **公平性**: 避免短序列饿死长序列
3. **预测**: 难以预测最优批次大小
4. **开销**: 批次重组的计算开销


## 相关概念

- [[paged-attention]]
- [[vllm]]
