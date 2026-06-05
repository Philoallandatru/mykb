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
  - inference
---

# Tutti

## 📋 基本信息

**类型**: 系统软件 / GPU存储优化  
**类别**: LLM推理优化  
**状态**: 已集成到vLLM  
**论文**: [arXiv:2605.03375](https://arxiv.org/abs/2605.03375)

## 📝 描述

Tutti是一个GPU中心的KV缓存对象存储系统，用于长上下文LLM推理服务。它通过消除CPU干预，实现了实用的SSD-backed KV缓存方案。

### 核心功能

**问题解决**:
- 长上下文LLM的KV缓存超出GPU内存
- 现有SSD卸载方案性能差（I/O碎片化、CPU瓶颈）
- GPU Direct Storage仍是"CPU中心"架构

**技术创新**:
1. **GPU原生对象抽象** - 批量KV缓存管理
2. **GPU io_uring** - 异步GPU直接对象I/O
3. **松弛感知调度** - 防止GPU资源竞争

### 性能表现

与GDS-enabled LMCache对比：
- TTFT降低 78.3%
- 请求处理速率提升 2倍
- 服务成本降低 27%
- 接近DRAM性能，容量无限

## 🔗 相关笔记

### 概念
- [[kv-cache|KV缓存]]
- [[io-uring|io_uring]]
- [[gpu-direct-storage|GPU Direct Storage]]

### 相关工具
- [[vllm|vLLM]] - 已集成Tutti
- [[lmcache|LMCache]] - 对比基准

### 论文笔记
- [[tutti-paper-2605.03375|Tutti论文完整笔记]]

## 💡 使用场景

### 适用情况
- **长上下文推理** - 序列长度 > 100K tokens
- **内存受限** - GPU HBM不足
- **成本敏感** - SSD比GPU内存便宜10倍以上
- **高吞吐需求** - 需要高请求处理速率

### 技术要求
- NVMe SSD（PCIe 4.0+推荐）
- CUDA兼容GPU
- vLLM框架

## 🎯 关键指标

| 指标 | 数值 |
|------|------|
| TTFT改进 | -78.3% |
| 吞吐量提升 | 2x |
| 成本降低 | -27% |
| SSD带宽利用 | ~100% |
| GPU停顿 | 接近零 |

## 💭 评价

### 优势
- ✅ 性能接近DRAM方案
- ✅ 容量几乎无限（SSD）
- ✅ 成本大幅降低
- ✅ 已集成主流框架（vLLM）

### 考虑因素
- SSD寿命（写入密集型）
- NVMe带宽限制
- 需要硬件支持（GPU Direct Storage）

### 技术意义
- **范式转变**: GPU中心 vs CPU中心
- **启发价值**: 将异步I/O模式引入GPU生态
- **实用价值**: 让长上下文LLM服务经济可行

---

*创建于: 2026-06-04*
*来源: [Tutti论文](https://arxiv.org/abs/2605.03375)*
