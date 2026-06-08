---
type: 推理优化库
tags:
- llm-inference
- cuda
- attention
created: '2026-06-08'
links:
  github: https://github.com/flashinfer-ai/flashinfer
  docs: https://docs.flashinfer.ai/
---

# flashinfer

## 概述

FlashInfer 是一个专注于 LLM 推理性能优化的开源库，提供高效的 attention 计算内核。

## 核心功能

### Attention 内核
- **Prefill**: 处理输入 prompt 的并行计算
- **Decode**: 处理自回归生成的增量计算
- **Paged Attention**: 支持 vLLM 的分页内存管理

### JIT 编译
- 根据运行时参数动态生成优化内核
- 缓存机制避免重复编译
- 支持多种数据类型和精度

### 多场景优化
- 单查询批处理
- 多查询批处理
- 可变序列长度

## 集成框架

- **vLLM**: 可选 attention 后端
- **SGLang**: 默认 attention 后端
- **LMDeploy**: 实验性支持

## 技术优势

1. **性能**: 比标准 PyTorch 实现快 2-5x
2. **灵活性**: JIT 编译适应不同配置
3. **内存效率**: 支持 Paged Attention

## 使用方式

```python
import flashinfer

# 创建 wrapper
wrapper = flashinfer.BatchDecodeWithPagedKVCacheWrapper(...)

# 执行 attention
output = wrapper.forward(q, kv_cache, ...)
```

## 链接

- **GitHub**: https://github.com/flashinfer-ai/flashinfer
- **文档**: https://docs.flashinfer.ai/
- **Paper**: [链接待补充]


## 相关概念

- [[vllm]]
- [[sglang]]
- [[kv-cache]]
