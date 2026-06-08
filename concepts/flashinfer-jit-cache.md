---
aliases:
- flashinfer缓存
- flashinfer-cache
tags:
- llm-inference
- cuda
- jit
- performance-optimization
created: '2026-06-08'
---

# flashinfer-jit-cache

## 定义

FlashInfer JIT Cache 是 FlashInfer 库的即时编译缓存机制，用于存储根据运行时参数编译的 CUDA 内核。

## 核心特性

### 动态编译
- 根据实际运行参数（序列长度、批次大小、头数）生成优化内核
- 避免静态编译带来的通用性损失

### 缓存机制
- **存储位置**: `~/.cache/flashinfer/` (默认)
- **缓存键**: 参数哈希值
- **淘汰策略**: LRU
- **持久化**: 跨进程、跨会话复用

### 性能影响
- **首次编译**: 1-5 秒延迟
- **缓存命中**: < 100ms 加载时间
- **启动优化**: 减少 95%+ 的冷启动时间

## 应用场景

1. **LLM 推理服务** - vLLM、SGLang 等框架
2. **开发环境** - 频繁重启时避免重复编译
3. **多模型部署** - 不同模型共享缓存

## 配置管理

```bash
# 自定义缓存位置
export FLASHINFER_CACHE_DIR=/ssd/flashinfer-cache

# 限制缓存大小
export FLASHINFER_CACHE_SIZE_MB=2048
```

## 最佳实践

- **生产环境**: 预热缓存，使用持久化存储
- **开发环境**: 定期清理避免磁盘占用过多
- **容器部署**: 将缓存目录挂载为 volume

## 技术对比

| 特性 | FlashInfer JIT | torch.compile | Flash Attention |
|------|---------------|---------------|----------------|
| 编译时机 | 运行时 JIT | 运行时 JIT | 静态编译 |
| 缓存机制 | 文件系统缓存 | Triton 缓存 | 无需缓存 |
| 专注领域 | Attention | 通用图优化 | Attention |
| 灵活性 | 高 | 高 | 中 |



## 相关概念

- [[kv-cache]]
- [[vllm]]
- [[sglang]]
