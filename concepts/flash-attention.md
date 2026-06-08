---
aliases:
- flashattention
tags:
- attention
- optimization
- cuda
- memory-efficiency
created: '2026-06-09'
---

# flash-attention

## 定义

FlashAttention 是一种 IO 感知（IO-aware）的精确注意力算法，使用 tiling 技术减少 GPU 高带宽内存（HBM）和片上 SRAM 之间的内存读写次数。

## 背景：标准注意力的问题

### 计算复杂度
- 时间复杂度: O(n²) 其中 n 是序列长度
- 内存复杂度: O(n²) 用于存储注意力矩阵
- 长序列时成为瓶颈

### IO 瓶颈
- 标准实现需要多次在 HBM 和 SRAM 之间传输数据
- HBM 带宽限制导致实际性能远低于理论峰值
- 近似方法（如 sparse attention）通常无法实现实际加速

## FlashAttention 核心技术

### Tiling 策略
- 将注意力计算分割为小块（tiles）
- 每个块在 SRAM 中完成计算
- 减少对 HBM 的访问次数

### 算法流程
1. 将 Q、K、V 矩阵分块加载到 SRAM
2. 在 SRAM 中计算注意力分数
3. 增量更新输出和 softmax 统计量
4. 避免在 HBM 中存储完整的 n×n 注意力矩阵

### IO 复杂度分析
- **标准注意力**: O(n²) HBM 访问
- **FlashAttention**: O(n²/M) HBM 访问，其中 M 是 SRAM 大小
- 典型减少 10-20 倍 HBM 访问

## 性能数据

### 训练加速
- **GPT-2** (1K 序列): 3× 加速
- **Long-range Arena** (1K-4K): 2.4× 加速  
- **BERT-large** (512): 15% 加速
- **MLPerf 1.1**: BERT 训练世界纪录

### 长上下文能力
- **Path-X** (16K): 61.4% 准确率（首次优于随机）
- **Path-256** (64K): 63.1% 准确率
- 使 Transformer 能处理之前无法处理的长序列任务

### 内存节省
- 序列长度 64K: 节省 ~10-20× 内存
- 使得可以在单 GPU 上训练更长的序列

## 技术细节

### 前向传播
- 使用 online softmax 技巧增量计算
- 分块加载 Q、K、V
- 在 SRAM 中完成 softmax 和矩阵乘法

### 反向传播
- 重计算注意力矩阵（recomputation）
- 避免存储 n×n 矩阵
- 权衡计算换内存

## FlashAttention-2 改进

- 更好的并行化策略
- 减少非矩阵乘法操作
- 2× 额外加速

## 应用场景

1. **长上下文训练**: 64K+ token 序列
2. **高效推理**: 降低内存和延迟
3. **多模态模型**: 处理长序列（如高分辨率图像）
4. **研究**: 探索长程依赖任务

## 与其他技术的关系

- **Sparse Attention**: FlashAttention 保持精确计算
- **Linear Attention**: 近似方法，FlashAttention 精确
- **vLLM/SGLang**: 推理框架中集成 FlashAttention

## 实现和可用性

- **官方实现**: CUDA/Triton
- **集成**: PyTorch 2.0+、Transformers、vLLM、SGLang
- **硬件要求**: 现代 NVIDIA GPU (Ampere+)

## 论文信息

- **标题**: FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness
- **会议**: NeurIPS 2022
- **作者**: Tri Dao, Daniel Y. Fu 等（Stanford, University of Washington）
- **论文**: https://arxiv.org/abs/2205.14135


## 相关概念

- [[kv-cache]]
- [[vllm]]
