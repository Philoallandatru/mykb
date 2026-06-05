---
type: raw
source: arxiv
url: https://arxiv.org/abs/2605.03375
date: 2026-06-04
status: pending
tags:
  - paper
  - llm
  - systems
  - performance
---

# Tutti: SSD-Backed KV Cache for Long-Context LLM Serving

## 📋 元数据

**标题**: Tutti: Making SSD-Backed KV Cache Practical for Long-Context LLM Serving  
**作者**: Shi Qiu, Yifan Hu, Xintao Wang, Wenhao Zhu, Jianqin Yan, Hao Chen, Kaiqiang Xu, Kai Chen, Yiming Zhang  
**提交日期**: 2026年5月5日  
**分类**: 计算机科学 - 操作系统  
**ArXiv ID**: 2605.03375

## 🎯 核心问题

当LLM的键值（KV）缓存因内存限制被卸载到NVMe SSD时，会遇到严重的性能瓶颈。当前方案在从SSD恢复KV缓存时表现不佳，主要原因：

1. **碎片化GPU内存布局** → 产生大量微小的随机I/O操作
2. **CPU瓶颈** → 即使使用GPU Direct Storage (GDS)，CPU仍需介入每个I/O操作
3. **"CPU中心"架构** → GDS本质上仍是CPU驱动的

## 💡 主要贡献

**Tutti**: 一个GPU中心的KV缓存对象存储系统

核心创新：**消除HBM与SSD之间数据和I/O控制路径中的CPU干预**

CPU角色降级为：每层仅异步加载一次I/O内核

## 🔧 关键技术设计

### 1. GPU原生对象抽象
- 支持批量KV缓存传输和管理
- 避免碎片化的小I/O操作

### 2. GPU io_uring
- 通过重构GPU存储栈支持异步GPU直接对象I/O
- 借鉴Linux io_uring设计，但完全在GPU上实现

### 3. 松弛感知I/O调度
- 防止GPU资源竞争
- 智能调度I/O以避免计算停顿

## 📊 实验结果

与启用GDS的、基于SSD的LMCache相比：

| 指标 | 改进 |
|------|------|
| **TTFT (首字节时间)** | ↓ 78.3% (在严格SLO约束下) |
| **请求处理速率** | ↑ 2倍 |
| **服务成本** | ↓ 27% |
| **SSD带宽利用** | 接近饱和，GPU停顿接近零 |

**关键发现**: 性能几乎匹配基于DRAM的方案，同时提供几乎无限的容量

## 🔗 相关概念

- [[KV-Cache|KV缓存]]
- [[GPU-Direct-Storage|GPU Direct Storage]]
- [[io-uring|io_uring]]
- [[LLM-Serving|LLM推理服务]]
- [[Memory-Hierarchy|内存层次结构]]

## 🔗 相关实体

- [[vLLM|vLLM]] (已集成Tutti)
- [[NVMe-SSD|NVMe SSD]]
- [[CUDA|CUDA]]

## 💭 个人思考

### 为什么重要？
1. **长上下文LLM的实用性** - 解决KV缓存内存墙问题
2. **成本效益** - 用廉价SSD替代昂贵GPU内存
3. **性能突破** - GPU中心设计是系统架构的范式转变

### 应用场景
- 长对话历史
- 大规模文档分析
- RAG系统
- 多轮对话

### 技术启示
- **去CPU化趋势** - 将更多控制逻辑移至GPU
- **异步I/O的重要性** - io_uring模式在GPU上的应用
- **对象级抽象** - 比块级I/O更适合GPU工作负载

## 📚 待深入

- [ ] 阅读io_uring在GPU上的具体实现细节
- [ ] 了解vLLM如何集成Tutti
- [ ] 研究松弛感知调度算法
- [ ] 探索其他GPU存储加速技术

---

*摄取日期: 2026-06-04*
