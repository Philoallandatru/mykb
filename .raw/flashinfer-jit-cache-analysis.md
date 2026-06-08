# FlashInfer JIT Cache 完整技术分析

## 概述

FlashInfer 是一个专注于 LLM 推理性能优化的库，提供高效的 attention 内核实现。其 JIT (Just-In-Time) 缓存机制是性能优化的关键组件。

## 核心架构

### 1. JIT 编译流程

- **输入参数**: 序列长度、批次大小、头数、数据类型
- **编译过程**: 根据参数生成定制化的 CUDA 内核
- **缓存存储**: 编译后的内核存储在本地文件系统

### 2. 缓存策略

- **缓存键**: 基于内核参数的哈希值
- **存储位置**: `~/.cache/flashinfer/` 或通过环境变量配置
- **缓存大小**: 可通过配置限制
- **淘汰策略**: LRU (Least Recently Used)

### 3. 性能优化

- **首次编译**: 可能需要 1-5 秒
- **缓存命中**: 加载时间 < 100ms
- **内存占用**: 每个内核约 1-10 MB

## 实际应用

### vLLM 集成

vLLM 使用 FlashInfer 作为 attention 后端之一，JIT 缓存加速模型启动。

### SGLang 集成

SGLang 默认使用 FlashInfer，JIT 缓存减少冷启动延迟。

## 配置与调优

### 环境变量

```bash
# 设置缓存目录
export FLASHINFER_CACHE_DIR=/path/to/cache

# 设置缓存大小限制 (MB)
export FLASHINFER_CACHE_SIZE_MB=1024

# 禁用缓存（调试用）
export FLASHINFER_DISABLE_CACHE=1
```

### 最佳实践

1. **预热**: 在生产环境启动前运行预热脚本
2. **持久化**: 将缓存目录挂载到持久存储
3. **监控**: 跟踪缓存命中率和编译时间
4. **清理**: 定期清理过期的缓存文件

## 性能数据

- **无缓存**: 首次启动 ~5 秒编译时间
- **有缓存**: 启动时间减少到 ~100ms
- **缓存命中率**: 生产环境通常 > 95%

## 故障排查

### 常见问题

1. **权限错误**: 确保缓存目录可写
2. **磁盘满**: 检查缓存目录大小
3. **CUDA 版本不匹配**: 清空缓存重新编译

## 与其他技术对比

### vs torch.compile
- FlashInfer: 专注 attention 内核
- torch.compile: 通用图优化

### vs Flash Attention
- FlashInfer: JIT 编译 + 多场景优化
- Flash Attention: 静态编译的单一实现

## 参考资料

- FlashInfer GitHub: https://github.com/flashinfer-ai/flashinfer
- 技术文档: https://docs.flashinfer.ai/
