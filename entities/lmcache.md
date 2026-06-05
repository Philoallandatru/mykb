---
type: entity
entity_type: tool
category: 系统软件
created: 2026-06-04
updated: 2026-06-04
tags:
  - entity
  - tool
  - llm
  - caching
  - distributed-systems
---

# LMCache

## 📋 基本信息

**类型**: 分布式KV缓存系统  
**类别**: LLM推理优化  
**开发者**: LMCache团队  
**官网**: https://docs.lmcache.ai/  
**集成**: vLLM, SGLang

## 📝 描述

LMCache 是专为大语言模型推理设计的分布式KV缓存系统，支持将KV缓存卸载到CPU RAM、本地磁盘(SSD)和远程存储，解决长上下文LLM的GPU内存瓶颈问题。

### 核心功能

**多层缓存架构**:
- **GPU HBM** - 最快，容量最小（40-80GB）
- **CPU RAM** - 快速，中等容量
- **Local Disk (SSD)** - 大容量，可接受延迟
- **Remote Storage** - 无限容量，跨节点共享

**关键特性**:
1. **Chunk-based Storage** - 按256 tokens为单位存储KV
2. **LRU驱逐策略** - 自动管理缓存容量
3. **Prefix Matching** - 前缀匹配优化缓存命中
4. **Multi-path Support** - 支持多NVMe设备并行

### 配置示例

**磁盘缓存配置**:
```yaml
chunk_size: 256
local_cpu: false          # 禁用CPU层直接测磁盘
max_local_cpu_size: 5.0
local_disk: "file:///path/to/cache/"
max_local_disk_size: 20.0
```

**vLLM集成**:
```bash
vllm serve model_name \
  --kv-transfer-config \
  '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'
```

### 性能表现

根据实际压力测试（Qwen2.5-1.5B-Instruct）:

| 场景        | TTFT (Cold) | TTFT (Warm) | 加速比        |
| --------- | ----------- | ----------- | ---------- |
| 长上下文重复请求  | 2.947s      | 0.053s      | **56.10x** |
| 不同上下文     | -           | -           | 1.08x      |
| 超高并发(500) | -           | -           | 稳定         |

**1小时持续压测结果**:
- 请求数: 560 (100% 成功)
- 缓存增长: 3.79 GB → 18.87 GB
- 文件数: 554 → 2,761
- 零错误，完全稳定

## 🔗 相关笔记

### 概念
- [[kv-cache|KV缓存]]
- [[lru-cache|LRU缓存算法]]
- [[distributed-cache|分布式缓存]]
- [[memory-hierarchy|内存层次结构]]
- [[ai-ssd]] - AI SSD 针对 LMCache 类 workload 优化 p99 延迟和混合读写 QoS

### 相关工具
- [[vllm|vLLM]] - 主要集成框架
- [[sglang|SGLang]] - 另一个支持的推理引擎
- [[tutti|Tutti]] - GPU中心的替代方案

### 实验笔记
- [[.raw/lmcache-multi-ssd-stress-test|LMCache多SSD压力测试实验]]

## 💡 使用场景

### 适用情况
- **长对话历史** - 数千轮对话上下文
- **重复长前缀** - 系统提示词 + 不同用户问题
- **RAG系统** - 大量检索上下文
- **代码补全** - 大型代码库上下文

### 配置策略选择

**CPU RAM offloading**:
- 快速（~10-20x 加速）
- 容量有限（几十GB）
- 适合：中等长度上下文

**Disk offloading**:
- 超大容量（TB级）
- 较慢（~50-100x 加速，取决于命中率）
- 适合：超长上下文，重复请求

**多路径配置**:
```bash
export LMCACHE_LOCAL_DISK="file:///mnt/nvme0/,file:///mnt/nvme1/,..."
export LMCACHE_LOCAL_DISK_PATH_SHARDING="by_gpu"
```

## 🎯 关键配置陷阱

### ❌ 常见错误

1. **local_cpu 混淆**
   - `local_cpu: true` 启用 CPU RAM 层
   - 不是磁盘缓存的开关！
   - 要测试纯磁盘性能需设为 `false`

2. **Prompt 太短**
   - chunk_size=256，prompts 需 > 1000 tokens
   - 太短会被 GPU prefix cache 吃掉
   - 磁盘缓存不会介入

3. **测试方法错误**
   - ❌ 100个不同prompts → 低命中率
   - ✅ 同一长prefix重复50次 → 高命中率

4. **Metrics 误判**
   - `/metrics` 端点可能显示 0
   - 实际看磁盘文件和日志
   - 关注 `LMCache hit tokens` 日志

## 📊 实测数据

### 缓存特性
- **写入速度**: 40-130 MB/s
- **文件大小**: ~7 MB per file (平均)
- **chunk数量**: ~60 chunks per 15K tokens
- **LRU触发**: 达到 max_local_disk_size 时自动驱逐

### 多SSD配置
- **by_gpu策略**: device_id % num_paths
- **单GPU限制**: 只使用第一块SSD
- **多GPU环境**: 每个GPU独立SSD路径

## 💭 评价

### 优势
- ✅ 真正的无限容量扩展
- ✅ 重复长上下文场景效果极佳（50x+）
- ✅ LRU自动管理，无需手动清理
- ✅ 生产环境验证（1小时零错误）
- ✅ 与主流框架深度集成

### 局限
- ⚠️ 单GPU多SSD收益有限
- ⚠️ 低缓存命中率场景加速不明显（<2x）
- ⚠️ 配置复杂，容易误判
- ⚠️ Metrics端点不总是准确

### 与Tutti对比

| 特性 | LMCache | Tutti |
|------|---------|-------|
| 架构 | CPU中心 | GPU中心 |
| 控制路径 | CPU介入 | GPU io_uring |
| 加速比 | 56x (测试) | 78.3% TTFT降低 |
| 成熟度 | 生产可用 | 较新 |
| 集成 | vLLM, SGLang | vLLM |

## 📚 参考资料

- [LMCache官方文档](https://docs.lmcache.ai/)
- [vLLM LMCache集成指南](https://docs.vllm.ai/en/v0.17.0/examples/others/lmcache/)
- [[.raw/lmcache-multi-ssd-stress-test|实验完整记录]]

---

*创建于: 2026-06-04*
*来源: LMCache多SSD压力测试实验*
