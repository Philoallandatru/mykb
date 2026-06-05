---
type: raw
source: conversation
date: 2026-06-03
status: pending
tags:
  - lmcache
  - ssd
  - performance-testing
  - llm
  - systems
---

# LMCache 多 SSD 压力测试实验记录

## 📋 实验背景

在 `~/ai-ssd` 项目中进行了为期约3小时的 LMCache 多 SSD 压力测试，验证 LMCache 磁盘缓存在长上下文 LLM 推理中的性能表现。

## 🎯 实验目标

1. 验证 LMCache 磁盘缓存是否正常工作
2. 测试多块 SSD (4块) 的负载均衡能力
3. 填满 20 GB 磁盘缓存并触发 LRU 驱逐
4. 测试 SSD IOPS 和吞吐量极限
5. 验证长时间（1小时）持续运行稳定性

## 🔧 技术栈

- **推理引擎**: vLLM
- **缓存系统**: LMCache
- **模型**: Qwen/Qwen2.5-1.5B-Instruct
- **存储**: 4块 NVMe SSD (C/D/E/F 盘)
- **配置**: 
  - chunk_size: 256 tokens
  - max_local_disk_size: 20 GB
  - max_model_len: 16384

## 📊 关键发现

### 1. 初始问题诊断 ❌

**问题**: 最初测试显示"磁盘缓存不工作"
- External prefix cache hit rate: 0.0%
- SSD 利用率: 0%
- 缓存文件: 126 MB (未增长)

**误判原因**:
1. **Prompt 太短** - 96 tokens << chunk_size (256)
2. **配置错误** - `LMCACHE_LOCAL_CPU=True` 启用了 CPU RAM 层，拦截了磁盘请求
3. **测试方法错误** - 使用了100个不同 prompts 而非重复相同长 prefix

### 2. 正确配置方案 ✅

```yaml
chunk_size: 256
local_cpu: false          # 关键：禁用 CPU 层直接测试磁盘
max_local_cpu_size: 5.0
local_disk: "file:///mnt/c/lmcache_test/"
max_local_disk_size: 20.0
```

**关键参数**:
```bash
--kv-transfer-config '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'
```

### 3. 验证成功 🎉

**测试配置**: 
- 使用 15,600 tokens 长上下文
- 同一个 prefix 重复请求 50 次

**结果**:
- ✅ 磁盘缓存: 763 MB (109 个 .pt 文件)
- ✅ 加速比: **56.10x** (2.947s → 0.053s)
- ✅ LMCache hit tokens: 15,104
- ✅ 成功率: 100%

## 📈 压力测试阶段

### 阶段 1: 极限填充
- **目标**: 填满 20 GB
- **结果**: 10.20 GB (1,492 文件)
- **加速比**: 1.09x (低命中率场景)

### 阶段 2: 持续填充
- **最终**: 16.69 GB (2,441 文件)
- **使用率**: 83.5%

### 阶段 3: 触发 LRU 驱逐
- **峰值**: 19.64 GB (2,873 文件)
- **驱逐**: -4.89 GB (-716 文件)
- **最终**: 14.75 GB (2,157 文件)
- ✅ LRU 机制正常工作

### 阶段 4: 超高并发
- **配置**: 500 并发请求
- **写入**: 3.79 GB (554 文件)
- **成功率**: 100%

### 阶段 5: 1小时持续压测
- **运行时间**: 60.57 分钟
- **请求数**: 560 (100% 成功)
- **缓存增长**: 3.79 GB → 18.87 GB (+15.08 GB)
- **文件数**: 554 → 2,761 (+2,207 文件)
- **平均吞吐**: 9.25 req/min

## 💡 核心洞察

### 1. LMCache 在高缓存命中率场景最优
- 相同 prefix 重复请求: **56x 加速**
- 不同 prompts: 1.08x 加速

### 2. 瓶颈分析
- ❌ 不是 SSD 性能瓶颈
  - 实际: 40-130 MB/s
  - 理论: 2-5 GB/s
- ✅ 是 GPU 推理速度瓶颈

### 3. 多 SSD 限制
- 单 GPU 环境下 `by_gpu` 策略只使用第一块 SSD
- 4块 SSD 配置中只有 C 盘被使用
- 需要多 GPU 或 RAID 0 才能利用所有磁盘

### 4. LRU 驱逐机制
- 自动管理缓存容量
- 达到上限时删除旧文件
- 保持在 20 GB 以内

## 🔗 相关概念

- [[kv-cache|KV缓存]]
- [[lmcache|LMCache系统]]
- [[vllm|vLLM推理引擎]]
- [[io-uring|io_uring异步IO]]
- [[ssd-performance|SSD性能优化]]
- [[lru-cache|LRU缓存算法]]

## 🔗 相关实体

- [[qwen|Qwen模型]]
- [[nvme-ssd|NVMe SSD]]

## 📚 生成的文档

1. `LMCACHE_DISK_STRESS_TEST_FINAL_REPORT.md` - 初始验证报告
2. `LMCACHE_EXTREME_STRESS_FINAL_REPORT.md` - 极限压力报告
3. `LMCACHE_SSD_STRESS_COMPLETE_SUMMARY.md` - 完整总结
4. `TEST_STATUS.md` - 实时状态监控

## 💭 个人思考

### 技术收获
1. **配置重要性**: `local_cpu` 参数决定了缓存层级
2. **测试设计**: 长上下文 + 重复 prefix 才能真正触发磁盘缓存
3. **Metrics 局限**: metrics 端点显示为 0 但实际缓存工作正常
4. **系统瓶颈**: 需要从整体视角看瓶颈（GPU vs SSD）

### 实用价值
- ✅ 证明 LMCache 磁盘缓存在生产环境可用
- ✅ 56x 加速对重复长上下文场景价值巨大
- ✅ 1小时稳定运行验证了可靠性
- ⚠️ 单 GPU 环境多 SSD 收益有限

### 待深入
- [ ] 多 GPU 环境下的多 SSD 负载均衡
- [ ] RAID 0 配置的性能对比
- [ ] 更长时间（24小时）的稳定性测试
- [ ] 与 Tutti 系统的性能对比

## 📊 最终统计

| 指标 | 数值 |
|------|------|
| 总测试时长 | ~3 小时 |
| 总请求数 | ~800+ |
| 总数据量 | ~30 GB+ |
| 最高加速比 | 56.10x |
| 成功率 | 100% |
| SSD 峰值使用 | 19.64 GB |

---

*摄取日期: 2026-06-04*
*来源: LMCache 多 SSD 压力测试对话*
