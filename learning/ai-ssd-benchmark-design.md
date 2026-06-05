# AI SSD Benchmark 设计学习笔记

## 核心洞察

传统存储 benchmark（CrystalDiskMark、ATTO）只测峰值带宽和 4K random，无法反映 AI PC 的真实工作负载。AI SSD benchmark 需要从"峰值性能"转向"真实场景 + 长尾延迟 + 混合负载 QoS"。

## 1. Benchmark 设计四层架构

AI SSD benchmark 应该分四层，而不是单一维度：

### Layer 1: Micro Benchmark
测 SSD 原始能力（顺序读写、4K random、不同 QD）

### Layer 2: AI I/O Pattern Benchmark
模拟 AI PC 典型 I/O（64K~256K random read、混合读写、后台写入+前台读）

### Layer 3: Application Benchmark
跑真实 LLM / RAG / Recall-like / 多模态应用

### Layer 4: Stress + QoS Benchmark
看长尾、温度、GC、多任务、低功耗

**Why**: 只看 Layer 1 会误导优化方向；只看 Layer 3 难以定位瓶颈；四层结合才能全面评估。

**How to apply**: 设计 AI SSD benchmark 套件时，每层都要覆盖，并建立层与层之间的关联（例如 Layer 2 的 64K random read p99 能否解释 Layer 3 的 KV cache 性能）。

---

## 2. 推荐的 8 个核心 Workload

建议定义：**AI-PC Storage Benchmark v0.1**，包括 8 个 workload：

| Workload     | 模拟场景             | 核心指标                  | 主要 I/O               | 为什么重要                           |
| ------------ | ---------------- | --------------------- | -------------------- | ------------------------------- |
| AI-Load      | 本地模型加载           | load time / TTFT      | 大文件顺序读 + metadata    | 用户首次体验，模型切换频率高                  |
| AI-RAG-Build | 知识库建库            | docs/s / build time   | 小文件读 + 随机写           | 建库是用户首次设置的门槛，影响采用意愿             |
| AI-RAG-Query | 本地语义搜索           | query p95/p99         | 小块随机读                | 查询是高频操作，p99 影响用户感知              |
| AI-Memory    | Recall-like 后台记忆 | foreground p99        | 后台小写 + 前台读           | 后台常驻，不能拖慢前台应用                   |
| AI-KV        | SSD KV cache     | TTFT / tokens/s / p99 | 64K~256K random read | 长上下文场景，SSD 成为 memory tier        |
| AI-Creator   | 图片/视频生成          | pipeline time         | 模型读 + 素材读写           | 多模态 AI 创作是 AI PC 重要卖点            |
| AI-CodeAgent | 代码 Agent         | agent step latency    | metadata + 小文件       | 开发者是 AI PC 早期采用者，影响口碑            |
| AI-Multitask | 多任务 QoS          | 前台抖动                  | 混合读写                 | 真实场景不会只跑一个任务，QoS 是关键差异化因素 |

**Why**: 这 8 个 workload 覆盖了 AI PC 的核心使用场景，每个都有明确的用户体验指标和 I/O 特征。

**How to apply**: 每个 workload 都要测三种状态（Fresh / Aged / Thermal stressed）和四种空盘率（20% / 50% / 80% / 90%），因为 AI PC 很可能长期接近满盘。

---

## 3. 指标体系：不要只看 MB/s

AI SSD benchmark 至少要分三类指标，不能只看吞吐量：

### 用户体验指标（最重要）
- 应用启动时间
- 模型加载时间
- TTFT
- tokens/s
- RAG query latency p50/p95/p99
- 搜索结果返回时间
- AI agent 单步耗时
- 前台卡顿时间

### SSD 内部指标
- read latency p50/p95/p99/p999（不只是平均值）
- write latency p50/p95/p99/p999
- mixed workload QoS
- SLC cache hit / miss
- GC count
- WAF
- thermal throttling point
- NAND busy time
- queue depth distribution

### 系统级指标
- CPU/GPU/NPU utilization
- DRAM pressure
- storage stack latency
- BitLocker on/off 差异
- battery power
- Modern Standby resume latency

**Why**: p99 latency、温度、功耗、混合负载 QoS 往往比峰值顺序读更能反映 AI PC 实际体验。一个在 CrystalDiskMark 跑 7GB/s 的 SSD，可能在 RAG query p99 上输给跑 5GB/s 但延迟稳定的 SSD。

**How to apply**: benchmark 报告中，用户体验指标放在最前面，用粗体突出；SSD 内部指标用于解释用户体验；系统级指标用于定位瓶颈是否在 SSD。

---

## 4. 针对 64K~256K random read 做 profile

传统 benchmark 只测 4K random，但 AI KV cache、向量 chunk、模型 shard 并不总是 4K。

建议新增内部 profile：
- 4K random read
- 16K random read
- 64K random read
- 128K random read
- 256K random read
- 1MB random read

**重点看**：
- QD=1/4/8/16（不只是 QD=32 峰值）
- p95/p99/p999（不只是平均）
- mixed read/write 下的抖动

**Why**: KV cache 更常见的是几十 KB 到几百 KB 的块，且对 tail latency 极其敏感。只测 4K random 会误导固件优化方向。

**How to apply**: 使用 fio 的 `bs=64K,128K,256K` 和 `lat_percentiles=1` 来测试；在固件侧做 read command coalescing 和 mapping cache 优化。

---

## 5. 低 QD 顺序读比高 QD 峰值更重要

很多 PC SSD 的宣传峰值来自高 QD 顺序读，但模型加载常常是：
- 低 QD（QD=1/2/4）
- 单进程
- mmap
- 多 shard
- 小 metadata + 大 tensor 混合

**测试方法**：
```
读取 40GB GGUF 单文件
读取 40GB safetensors 16 shards
读取 40GB safetensors 64 shards
比较 cold load / warm load / thermal aged load
```

**Why**: 真实模型加载不会发起 QD=32 的请求，用户感知的是首字节延迟和稳定吞吐，而不是理论峰值。

**How to apply**: 固件要做 stream detection、aggressive read-ahead、HMB/DRAM mapping cache；benchmark 要测 QD=1/2/4 的顺序读，而不是只测 QD=32。

---

## 6. RAG 场景比纯 LLM 更能体现 SSD 价值

RAG 的瓶颈经常不是 compute，而是**索引、metadata、chunk 原文、向量文件的随机访问路径**。

典型 RAG pipeline：
1. 读取 10GB/50GB/100GB 文档
2. parse / OCR / chunk / embedding
3. 写入向量库（FAISS / LanceDB / Chroma）+ metadata（SQLite / DuckDB）
4. 查询时 top-k retrieval + 读取原文 chunk
5. 拼 prompt 给 LLM

**关键 I/O 特征**：
- 索引构建：小文件读 + 随机写 + fsync
- 查询：4K~128K random read + p99 latency
- 后台更新：低优先级写入和 compaction

**Why**: 如果 SSD 的 4K~128K random read p99 很高，或者后台 compaction 拖慢前台 query，RAG 体验会非常糟糕，即使 LLM 本身很快。

**How to apply**: 设计 AI-RAG-Build 和 AI-RAG-Query 两个独立 benchmark；在固件侧优化 SQLite / RocksDB / DuckDB 类 workload 的 fsync/flush latency 和 GC throttling。

---

## 7. 后台 AI Memory：低干扰比高吞吐更重要

Recall-like 系统会长期写入，但用户不希望机器卡。

**测试方法**：
- 8 小时后台 snapshot 写入（每 5~10 秒一条，包含 screenshot + OCR + embedding）
- 每 30 秒发起一次 RAG query
- 记录 query p99、SSD 温度和功耗

**固件策略**：
- background write throttle
- foreground read boost
- idle-time GC
- thermal-aware background scheduling
- power-state aware writeback

**Why**: 后台写满速不是目标，前台读不爆尾延迟才是。如果后台 AI memory 写入导致前台应用卡顿，用户会关闭这个功能。

**How to apply**: benchmark 不要只测后台写入的吞吐量，要测"后台写入 + 前台读"的混合场景，看前台 read p99 是否恶化。

---

## 8. Thermal：AI PC 是长跑，不是短跑

AI PC workload 特点：
- 模型加载：短时间高读
- RAG 建库：长时间读写
- Recall：长时间低速写
- Agent：间歇突发
- 多模态生成：读写混合 + GPU 高温环境

**固件优化**：
- 更平滑的 thermal throttling 曲线（避免突然从 7GB/s 掉到 1GB/s）
- 温度接近阈值时优先保证 read latency，可以降低 write 速度
- 后台写入主动降速
- 温度恢复后的性能回升策略

**测试指标**：
- time_to_throttle
- performance_after_5min
- performance_after_30min
- p99_latency_under_thermal

**Why**: 传统 benchmark 测 30 秒或 1 分钟就停了，但 AI PC 可能连续跑几小时。温控不平滑会导致用户体验剧烈波动。

**How to apply**: benchmark 要跑长时间测试（2 小时 / 8 小时 / 72 小时），记录温度曲线和性能曲线，看是否平滑。

---

## 9. Power：电池模式下的 TTFT 稳定性

AI PC 不只是台式机，也包括轻薄本。NPU 本地 AI 很多是在电池模式下跑。

**固件关注**：
- APST/ASPM 状态切换延迟
- idle power
- burst read 后快速回低功耗
- 低功耗状态下的小随机读唤醒延迟
- Modern Standby 下后台 AI memory 写入

**测试场景**：
- AC mode
- Battery saver
- Balanced mode
- Modern Standby resume
- NPU inference + SSD query

**Why**: 电池模式下 TTFT 稳定性比极限带宽更重要。如果低功耗状态唤醒延迟高，每次 RAG query 都会有明显卡顿。

**How to apply**: benchmark 要分别测试 AC 和电池模式，看 p99 latency 差异；固件要优化 idle→active 的唤醒路径。

---

## 10. Security：本地隐私 AI 数据增加安全要求

AI PC 会把更多敏感数据放本地：
- 屏幕快照
- OCR 文本
- 邮件索引
- 聊天历史
- embedding
- 个人文件摘要

**固件/产品层面要考虑**：
- TCG Opal / Pyrite
- namespace sanitize
- secure erase / crypto erase
- PLP 或至少 metadata consistency
- power loss 下数据库一致性
- BitLocker 场景性能

**Why**: 微软 Recall 明确说数据保存在本地并加密，不上传。如果 SSD 在 BitLocker 开启下性能崩溃，或者 power loss 导致数据库损坏，会严重影响用户信任。

**How to apply**: benchmark 要测 BitLocker on/off 的性能差异；固件要优化加密场景的 flush/FUA latency；产品要支持 secure erase 而不是只支持 format。

---

## 11. 具体 fio pattern 建议

### 模型加载模拟
```
bs=1M
rw=read
iodepth=1/2/4
numjobs=1/4
size=40G
direct=1
```

### RAG query 模拟
```
bs=4K,16K,64K
rw=randread
iodepth=1/4/8/16
lat_percentiles=1
```

### KV cache 模拟
```
bs=64K,128K,256K
rw=randread
iodepth=4/8/16/32
numjobs=1/2/4
lat_percentiles=1
```

### 后台 Recall-like 写入 + 前台检索
```
job1:
  rw=write
  bs=64K
  rate=20M~200M
  iodepth=1

job2:
  rw=randread
  bs=4K/64K
  iodepth=1/4
  latency_target
```

### RAG build 模拟
```
rw=randrw
rwmixread=60/70/80
bsrange=4K-256K
iodepth=4/8/16
```

**Why**: 这些 fio pattern 能模拟 AI PC 的真实 I/O，而不是只测峰值性能。

**How to apply**: 将这些 pattern 集成到自动化测试框架中，作为 Layer 2 (AI I/O Pattern Benchmark) 的一部分。

---

## 12. 固件优化优先级

### P0：必须做（影响所有 AI PC 场景）
1. Mixed read/write 下 read p99 latency 优化
2. 64K~256K random read profile
3. 低 QD 顺序读稳定性
4. thermal throttling 平滑化
5. aged drive 下 QoS
6. BitLocker / flush / FUA latency 测试

### P1：AI PC 强相关（影响 RAG 和 KV cache）
1. RAG / SQLite / DuckDB / vector DB workload profile
2. 后台写入不影响前台读
3. host stream hint / temperature-aware GC
4. 模型 shard 多文件读取优化
5. HMB mapping cache 策略优化

### P2：高级 AI SSD 差异化（未来方向）
1. KV cache read priority mode
2. AI workload detection
3. namespace / stream isolation
4. DirectStorage / GPU storage path 适配
5. Smart prefetch for model file layout
6. AI data secure erase / crypto erase workflow

**Why**: P0 是所有 AI PC 都需要的基础能力；P1 是 RAG 和 KV cache 的关键差异化；P2 是未来方向，可以作为高端产品的卖点。

**How to apply**: 按优先级分配固件开发资源，先做 P0，再做 P1，最后做 P2。不要一开始就追求 P2 的高级功能，而忽略了 P0 的基础体验。

---

## 核心结论

AI SSD benchmark 设计的核心思想：

> **从"峰值吞吐优先"转向"AI 前台读延迟、混合负载 QoS、长时间温控、隐私数据一致性优先"。**

关键差异：
- 不只测 4K random，要测 64K~256K random
- 不只测 QD=32 峰值，要测 QD=1/4 低队列深度
- 不只测平均值，要测 p95/p99/p999 长尾延迟
- 不只测单一任务，要测混合负载 QoS
- 不只测短时间，要测长时间温控
- 不只测 AC 模式，要测电池模式
- 不只测空盘，要测 aged drive
- 不只测未加密，要测 BitLocker

## 相关概念

- [[ai-ssd]] - AI SSD 的核心定义和优化方向
- [[kv-cache]] - KV cache 是 AI SSD 的重要应用场景
- [[lmcache]] - LMCache 的多层缓存架构可以指导 AI SSD benchmark 设计
- [[io-uring]] - io_uring 的异步 I/O 可以提升 AI PC 的存储性能

## 参考资料

完整分析见：[[../.raw/ai-ssd-comprehensive-analysis|AI SSD 工程化定义与 Benchmark 设计]]

---

**标签**: #learning #benchmark #ai-ssd #storage #optimization #testing
