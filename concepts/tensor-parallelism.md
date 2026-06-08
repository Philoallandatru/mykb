---
aliases:
- tp
- model-parallelism
tags:
- distributed-training
- parallelism
- llm-inference
created: '2026-06-09'
---

# tensor-parallelism

## 定义

Tensor Parallelism (张量并行) 是一种模型并行技术，将单个模型层的张量（权重矩阵、激活）切分到多个设备上并行计算。

## 核心原理

### 层内并行
- 每个 Transformer 层在多个 GPU 上分布
- 权重矩阵按列或按行切分
- 前向和反向传播需要跨 GPU 通信

### 切分策略

#### 列并行 (Column Parallel)
```
原始权重 W: [hidden_size, ffn_size]
切分到 N 个 GPU:
  GPU 0: W[:, 0:ffn_size/N]
  GPU 1: W[:, ffn_size/N:2*ffn_size/N]
  ...
```

**应用**: FFN 的第一个 linear、Attention 的 QKV 投影

#### 行并行 (Row Parallel)
```
原始权重 W: [ffn_size, hidden_size]
切分到 N 个 GPU:
  GPU 0: W[0:ffn_size/N, :]
  GPU 1: W[ffn_size/N:2*ffn_size/N, :]
  ...
```

**应用**: FFN 的第二个 linear、Attention 的输出投影

## Megatron-LM 实现

### Transformer Block 切分

**Self-Attention**:
1. QKV 投影: 列并行（每个 GPU 负责部分头）
2. Attention 计算: 各 GPU 独立
3. 输出投影: 行并行 + All-Reduce

**Feed-Forward Network**:
1. 第一个 Linear: 列并行
2. 激活函数: 各 GPU 独立
3. 第二个 Linear: 行并行 + All-Reduce

### 通信模式
- **前向**: 2 次 All-Reduce per layer
- **反向**: 2 次 All-Reduce per layer
- **总通信量**: O(hidden_size × seq_len × batch)

## 性能特性

### 优势
1. **显存效率**: 模型权重平均分布
2. **计算并行**: 矩阵乘法并行执行
3. **扩展性好**: 2-8 GPU 线性扩展

### 限制
1. **通信开销**: 频繁的 All-Reduce
2. **规模限制**: 通常不超过单节点（8 GPU）
3. **带宽敏感**: 需要高速互联（NVLink）

## 与其他并行技术对比

### Pipeline Parallelism
- **TP**: 层内切分，高通信频率
- **PP**: 层间切分，低通信频率
- **结合**: 常用 TP 在节点内，PP 跨节点

### Data Parallelism
- **TP**: 模型并行，权重分布
- **DP**: 数据并行，权重复制
- **结合**: ZeRO 混合两者优势

## 推理场景应用

### vLLM Tensor Parallelism
- 支持 TP 用于大模型推理
- 自动切分和通信管理
- 配置: `--tensor-parallel-size N`

### 性能考量
- **批次大小小**: 通信开销占比高
- **批次大小大**: 计算时间摊销通信
- **最佳规模**: 2-4 GPU 通常最优

## 实现细节

### 权重切分
```python
# 列并行 Linear
class ColumnParallelLinear(nn.Module):
    def forward(self, x):
        # x: [batch, seq, hidden]
        output = F.linear(x, self.weight)  # [batch, seq, hidden/N]
        # 无需 All-Gather，保持切分状态
        return output

# 行并行 Linear  
class RowParallelLinear(nn.Module):
    def forward(self, x):
        # x: [batch, seq, hidden/N] (已切分)
        output = F.linear(x, self.weight)  # [batch, seq, hidden]
        # All-Reduce 合并各 GPU 结果
        dist.all_reduce(output)
        return output
```

### 通信优化
1. **通信与计算重叠**: 异步 All-Reduce
2. **融合通信**: 合并多次小通信
3. **梯度累积**: 减少通信频率

## 配置指南

### 选择 TP Size
- **单 GPU 可容纳**: TP=1（无 TP）
- **单节点**: TP=2/4/8
- **多节点**: TP + PP 组合

### 硬件要求
- **互联**: NVLink (300+ GB/s) 或 InfiniBand
- **显存**: 每 GPU 至少容纳 1/N 模型
- **均衡性**: 所有 GPU 性能一致

## 调优技巧

1. **批次大小**: 增大以摊销通信
2. **序列长度**: 长序列更能发挥 TP 优势  
3. **混合精度**: FP16/BF16 减少通信量
4. **Profile**: 使用 nsys/nvprof 分析通信瓶颈

## 研究和发展

- **Sequence Parallelism**: 在序列维度并行
- **Expert Parallelism**: MoE 的专家并行
- **Auto-parallelism**: 自动搜索最优切分策略


## 相关概念

- [[vllm]]
- [[distributed-inference]]
