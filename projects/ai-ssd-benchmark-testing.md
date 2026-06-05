---
type: project
status: planned
priority: high
started: 
deadline: 
updated: 2026-06-05
tags:
  - project
  - ai-ssd
  - benchmark
  - storage
  - testing
---

# AI SSD Benchmark 测试项目

## 📋 概述

基于 [[ai-ssd|AI SSD]] 工程化定义，设计并实施完整的 AI-PC Storage Benchmark v0.1 测试套件，验证不同SSD在AI PC典型工作负载下的性能表现。

本项目旨在：
1. 实现四层Benchmark架构（Micro/Pattern/Application/Stress）
2. 测试8个核心workload的性能
3. 验证P0固件优化方向的有效性
4. 为AI SSD产品定义提供数据支撑

## 🎯 目标

### 核心目标
- [ ] 设计并实施完整的AI-PC Storage Benchmark v0.1测试套件
- [ ] 完成至少3款不同SSD的对比测试
- [ ] 生成包含用户体验指标、SSD内部指标、系统级指标的完整报告
- [ ] 验证 64K~256K random read、低QD顺序读、p99延迟等关键优化方向

### 次要目标
- [ ] 建立自动化测试框架
- [ ] 创建可视化性能对比dashboard
- [ ] 输出AI SSD选型指南
- [ ] 为固件团队提供优化建议

## 📝 任务清单

### Phase 1: 测试环境准备 (Week 1-2)
- [ ] 准备测试硬件
  - [ ] 选定3款测试SSD（不同品牌/控制器）
  - [ ] 准备测试主机（支持PCIe Gen4/Gen5）
  - [ ] 确认NPU/GPU配置
- [ ] 搭建测试环境
  - [ ] 安装 Windows 11 Pro (Copilot+ PC ready)
  - [ ] 安装 Linux 测试环境 (Ubuntu 22.04+)
  - [ ] 配置双系统或虚拟化环境
- [ ] 安装测试工具
  - [ ] fio
  - [ ] DiskSpd
  - [ ] nvme-cli
  - [ ] iostat / blktrace
  - [ ] LM Studio / Ollama
  - [ ] Python 测试脚本环境

### Phase 2: Layer 1 - Micro Benchmark (Week 2)
- [ ] 顺序读写测试
  - [ ] 大文件顺序读 (1M block, QD=1/2/4/8/16/32)
  - [ ] 大文件顺序写 (1M block, QD=1/2/4/8/16/32)
  - [ ] 记录温度曲线
- [ ] 随机读写测试
  - [ ] 4K random read (QD=1/4/8/16/32)
  - [ ] 16K random read (QD=1/4/8/16/32)
  - [ ] 64K random read (QD=1/4/8/16/32)
  - [ ] 128K random read (QD=1/4/8/16/32)
  - [ ] 256K random read (QD=1/4/8/16/32)
  - [ ] 记录 p50/p95/p99/p999 延迟
- [ ] 混合读写测试
  - [ ] 70/30 read/write mix
  - [ ] 80/20 read/write mix
  - [ ] 观察 read p99 在写入压力下的变化

### Phase 3: Layer 2 - AI I/O Pattern Benchmark (Week 3)
- [ ] 实现 fio 测试脚本
  - [ ] 模型加载模拟 (bs=1M, rw=read, QD=1/2/4)
  - [ ] RAG query 模拟 (bs=4K/16K/64K, rw=randread)
  - [ ] KV cache 模拟 (bs=64K/128K/256K, rw=randread)
  - [ ] 后台写入+前台读 (job1: write 64K, job2: randread 4K/64K)
  - [ ] RAG build 模拟 (rw=randrw, rwmixread=70, bsrange=4K-256K)
- [ ] 记录关键指标
  - [ ] 各场景下的 IOPS / throughput
  - [ ] p95/p99/p999 延迟分布
  - [ ] SLC cache 耗尽点
  - [ ] GC 触发频率

### Phase 4: Layer 3 - Application Benchmark (Week 4-5)
- [ ] **AI-Load**: 本地模型加载
  - [ ] 测试 Qwen2.5-1.5B (2GB)
  - [ ] 测试 Qwen2.5-7B (4GB)
  - [ ] 测试 Llama-3.1-8B (8GB)
  - [ ] 测试 Qwen2.5-32B (18GB)
  - [ ] 记录 cold load time / warm load time / TTFT
- [ ] **AI-RAG-Build**: 知识库建库
  - [ ] 准备测试数据集 (10GB / 50GB mixed documents)
  - [ ] 使用 LlamaIndex 或 LangChain 建库
  - [ ] 记录 docs/s / build time / SSD write throughput
- [ ] **AI-RAG-Query**: 本地语义搜索
  - [ ] 执行 1000 个随机 query
  - [ ] 记录 retrieval latency p50/p95/p99
  - [ ] 记录 TTFT 和 tokens/s
- [ ] **AI-Memory**: Recall-like 后台记忆
  - [ ] 模拟 8 小时后台 snapshot 写入
  - [ ] 每 30 秒发起前台 query
  - [ ] 记录前台 query p99 是否恶化
- [ ] **AI-KV**: SSD KV cache
  - [ ] 配置 [[lmcache|LMCache]] 纯 disk 模式
  - [ ] 测试长上下文场景 (32K/64K/128K tokens)
  - [ ] 记录 cache hit 下的 TTFT / tokens/s
- [ ] **AI-CodeAgent**: 代码 Agent
  - [ ] 准备大型 monorepo (100K files, 20GB)
  - [ ] 测试首次打开 repo 时间
  - [ ] 测试 symbol index 构建时间
  - [ ] 测试 Agent 单步响应延迟
- [ ] **AI-Multitask**: 多任务 QoS
  - [ ] 同时运行：RAG query + 后台索引 + 文件同步
  - [ ] 记录前台 TTFT 抖动情况

### Phase 5: Layer 4 - Stress + QoS Benchmark (Week 5-6)
- [ ] **Aged Drive 测试**
  - [ ] 预写至 50% / 80% / 90% 容量
  - [ ] 重复 Layer 2 和 Layer 3 关键测试
  - [ ] 对比 fresh vs aged 性能差异
- [ ] **Thermal Stress 测试**
  - [ ] 持续高负载 2 小时 / 8 小时
  - [ ] 记录温度曲线和性能曲线
  - [ ] 观察 thermal throttling 是否平滑
  - [ ] 测试 performance_after_5min / 30min
- [ ] **BitLocker 加密测试**
  - [ ] 开启 BitLocker
  - [ ] 重复关键测试
  - [ ] 对比加密 on/off 性能差异
- [ ] **电池模式测试**
  - [ ] 切换到 Battery Saver 模式
  - [ ] 测试 TTFT 稳定性
  - [ ] 测试低功耗唤醒延迟
- [ ] **Modern Standby 测试**
  - [ ] 测试睡眠唤醒后的性能恢复

### Phase 6: 数据分析与报告 (Week 7)
- [ ] 整理测试数据
  - [ ] 生成性能对比表格
  - [ ] 绘制延迟分布图
  - [ ] 绘制温度-性能曲线
- [ ] 撰写测试报告
  - [ ] Executive Summary
  - [ ] 8个workload详细结果
  - [ ] 3款SSD对比分析
  - [ ] P0优化方向验证结论
- [ ] 输出选型指南
  - [ ] 不同场景推荐的SSD特性
  - [ ] 性价比分析
- [ ] 固件优化建议
  - [ ] 针对发现的瓶颈提出改进方向

## 🔗 相关资源

### 概念和方法论
- [[ai-ssd]] - AI SSD 核心定义
- [[ai-ssd-benchmark-design|AI SSD Benchmark 设计]] - 详细方法论
- [[.raw/ai-ssd-comprehensive-analysis|完整技术分析]]

### 相关技术
- [[kv-cache]] - KV cache 场景理解
- [[lmcache]] - LMCache 工具用于 AI-KV 测试
- [[io-uring]] - Linux 异步 I/O
- [[gpu-direct-storage]] - GDS 可能影响测试结果

### 参考实验
- [[lmcache-ssd-stress-test|LMCache SSD 压力测试]] - 可借鉴的测试方法

### 工具和资源
- [fio 官方文档](https://fio.readthedocs.io/)
- [DiskSpd GitHub](https://github.com/Microsoft/diskspd)
- [LMCache 文档](https://docs.lmcache.ai/)
- [UL Procyon AI Benchmark](https://benchmarks.ul.com/procyon/ai-computer-vision)

## 📊 进度跟踪

**当前阶段**: 项目规划

**完成百分比**: 0%

### 里程碑
- [ ] Week 2: 测试环境就绪
- [ ] Week 3: Layer 1+2 完成
- [ ] Week 5: Layer 3 完成
- [ ] Week 6: Layer 4 完成
- [ ] Week 7: 报告输出

### 预计工作量
- **总时长**: 7 周
- **人力**: 1-2 人
- **硬件投入**: 3+ 块测试 SSD，1 台测试主机

## 💭 笔记

### 关键成功因素
1. **测试 SSD 选型要有代表性** - 不同控制器（Phison/SMI/自研）、不同 NAND（TLC/QLC）
2. **测试环境要稳定** - 避免其他进程干扰
3. **数据采集要全面** - 不只是平均性能，要记录 p99、温度、GC 事件
4. **真实应用测试很重要** - Layer 3 比 Layer 1/2 更能体现实际体验

### 潜在风险
1. **测试时间过长** - Layer 4 的 aging 和 thermal 测试需要数天
2. **应用环境搭建复杂** - RAG、LMCache、模型下载需要时间
3. **结果解读需要专业知识** - 需要理解 SSD 内部机制

### 优化建议
- 考虑并行测试（多台机器同时测不同 SSD）
- 编写自动化脚本减少手动操作
- 实时监控测试进度，及时发现异常

---

*创建于: 2026-06-05*
*基于: [[ai-ssd-benchmark-design|AI SSD Benchmark 设计方法论]]*
