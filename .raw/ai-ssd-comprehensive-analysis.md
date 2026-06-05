# AI SSD 工程化定义与 Benchmark 设计

> **AI SSD 不是"SSD 里塞一个 AI 芯片"这么简单，而是面向 AI PC 本地推理、RAG、向量索引、KV Cache、模型加载、多模态内容处理、隐私数据检索等场景，对读延迟、随机小块、并发 QoS、温控、掉电一致性、安全擦除/加密做专门优化的 SSD。**

AI PC 的趋势已经很明确：Copilot+ PC 把 **40+ TOPS NPU** 作为关键门槛，微软 Foundry Local 也在推动 LLM 直接在 Windows 设备本地运行；Recall 这类功能会把快照和上下文信息保存在本地硬盘并加密。

---

## 1. AI PC 下 AI SSD 的核心场景

### 场景 1：本地 LLM 模型加载 / 切换

典型行为：
- 用户打开 Copilot / LM Studio / Ollama / Foundry Local
- 从 SSD 读取 4GB ~ 80GB 模型文件
- 加载到 DRAM / VRAM / NPU runtime
- 开始推理

I/O 特征：
- 大文件顺序读为主
- 少量 metadata / tokenizer / config 小文件随机读
- 模型切换频繁时反复 cold load

用户感知指标：
- 模型首次可用时间
- TTFT
- 模型切换时间
- 应用启动时间

固件优化方向：
- 大文件顺序读吞吐稳定性
- 低 QD 下的顺序读性能
- read-ahead / stream detection
- HMB / DRAM cache 对 metadata 和模型头部的加速
- 温控下 sustained read
- Windows Modern Standby 唤醒后的快速恢复

---

### 场景 2：本地 RAG / 个人知识库 / 企业文档索引

典型行为：
- PDF / Word / 邮件 / 网页 / Jira / Confluence / 本地文件
- OCR / chunk / embedding
- 向量库 + 原文索引存到 SSD
- 用户提问时检索 top-k 文档
- LLM 生成答案

I/O 特征：
- 索引构建阶段：大量小文件读 + 顺序写 + 随机写
- 查询阶段：小块随机读 + mmap + SQLite / DuckDB / LanceDB / FAISS index 访问
- 后台更新阶段：低优先级写入和 compaction

用户感知指标：
- 首次建库时间
- 增量索引时间
- query latency p50 / p95 / p99
- top-k 检索时间
- 前台应用卡顿程度

固件优化方向：
- 4K~128K random read p99 latency
- 混合读写 QoS
- SQLite / RocksDB / DuckDB 类 workload 的 fsync / flush latency
- 小文件 metadata 加速
- GC throttling
- 写放大控制

---

### 场景 3：Windows Recall / 本地 AI Memory / 屏幕历史搜索

典型行为：
- 系统周期性保存屏幕快照
- OCR / image embedding / text embedding
- 写入本地加密数据库
- 用户搜索"上周看到的那个表格"
- 本地检索 + 回放

I/O 特征：
- 后台持续小写入
- 图片 / OCR 文本 / embedding 混合写入
- 前台搜索时随机读
- 加密文件系统 / BitLocker / Windows Hello 相关安全路径

Benchmark 重点：
- 后台持续写入对前台应用的影响
- 加密开启下的 p99 read/write latency
- 长时间运行后的 GC、SLC cache、温度影响
- 快照数据库膨胀后的 query latency

固件优化方向：
- 后台写入限速和 host hint 识别
- 前台读优先级
- 小写合并
- 加密场景下 flush / FUA latency 优化
- 低功耗状态切换不能影响后台 AI memory 写入

---

### 场景 4：SSD 作为 KV Cache / Memory Extension

典型行为：
- 本地 LLM 上下文很长
- DRAM / VRAM 放不下全部 KV Cache
- 把部分 KV Cache 放到 SSD
- 需要时从 SSD 拉回

I/O 特征：
- 大量小块随机读
- block size 可能是 16KB ~ 数百 KB
- 读请求和 GPU/NPU compute 强耦合
- p99 latency 比平均带宽更重要

用户感知指标：
- TTFT
- tokens/s
- 长上下文下响应是否卡顿
- context length 扩展能力
- GPU/NPU bubble time

固件优化方向：
- 低 QD / 中 QD random read tail latency
- 64K / 128K / 256K 小块随机读优化
- 多 stream / 多 namespace 隔离
- read priority / latency mode
- 避免 read 被 GC 或后台折叠阻塞
- 高温下仍保持 p99 latency 稳定

---

### 场景 5：多模态内容创作：图片、视频、音频、3D

典型行为：
- 本地 Stable Diffusion / 视频生成 / Whisper / OCR / 图像编辑
- 读取模型、LoRA、ControlNet、素材
- 生成中间文件、缓存、preview
- 写出图片 / 视频 / 音频

I/O 特征：
- 模型大文件顺序读
- 素材大量小文件随机读
- 中间缓存连续写 + 随机更新
- 多任务并发：AI 生成 + 浏览器 + 剪辑软件

---

### 场景 6：AI 开发者工作流：代码库索引、Agent、编译、测试

典型行为：
- VS Code / Cursor / Copilot / OpenCode / Claude Code
- 扫描代码库
- 构建 embedding / symbol index
- Agent 修改代码
- 频繁 git diff / search / test / build

I/O 特征：
- 大量小文件 metadata 操作
- 小文件随机读
- 增量写入
- 编译产物 burst write
- 并发后台索引

---

## 2. AI SSD Benchmark 设计

传统 CrystalDiskMark 只测峰值带宽和 4K random，不够。AI SSD benchmark 应该设计成四层：

1. **Micro Benchmark** - 看 SSD 原始能力
2. **AI I/O Pattern Benchmark** - 模拟 AI PC 典型 I/O
3. **Application Benchmark** - 跑真实 LLM / RAG / Recall-like / 多模态应用
4. **Stress + QoS Benchmark** - 看长尾、温度、GC、多任务、低功耗

---

## 3. 推荐 Benchmark 场景矩阵

### Benchmark A：Local LLM Model Load
测模型首次加载和切换体验

### Benchmark B：RAG Index Build
测个人知识库首次建库

### Benchmark C：RAG Query Latency
测本地语义搜索体验

### Benchmark D：Recall-like AI Memory
模拟 AI PC 常驻后台记忆系统

### Benchmark E：KV Cache / SSD Memory Extension
测 SSD 能不能承担长上下文 cache tier

### Benchmark F：AI Creator / 多模态生成
测 AI 图片、视频、音频创作对 SSD 的压力

### Benchmark G：AI Code Agent
测开发者 AI PC 场景

### Benchmark H：AI Multitasking QoS
真实 AI PC 不会只跑一个任务

---

## 4. 指标体系

### 用户体验指标
- 应用启动时间
- 模型加载时间
- TTFT
- tokens/s
- RAG query latency p50/p95/p99
- 搜索结果返回时间
- AI agent 单步耗时
- 前台卡顿时间

### SSD 内部指标
- read latency p50/p95/p99/p999
- write latency p50/p95/p99/p999
- mixed workload QoS
- SLC cache hit / miss
- GC count
- WAF
- thermal throttling point
- NAND busy time
- queue depth distribution

### 系统级指标
- CPU utilization
- GPU/NPU utilization
- DRAM pressure
- page fault
- storage stack latency
- BitLocker on/off 差异
- battery power
- Modern Standby resume latency

---

## 5. 固件优化策略

### 5.1 读优先：AI 前台请求不能被后台写拖死
- read-priority arbitration
- short-read fast path
- foreground queue 优先级
- GC 可中断 / 可让路
- write drain 不阻塞 latency-sensitive read

### 5.2 针对 64K~256K random read 做优化
- read command coalescing
- NAND die/channel 并行度调度
- mapping cache 命中优化
- 对中等 block read 避免过度拆分
- 减少跨 die read amplification

### 5.3 模型加载优化：低 QD 顺序读 + 多 shard 并发读
- stream detection
- aggressive read-ahead
- sequential read 稳态温控
- HMB / DRAM mapping cache
- 多文件 interleaved read 的预读策略

### 5.4 向量库 / SQLite / DuckDB / RocksDB 场景优化
- 小写合并
- FTL mapping cache 优化
- flush/FUA latency 优化
- SLC cache 分配给 metadata-heavy write
- 降低 write amplification
- 支持 host stream hint 区分 index / log / blob

### 5.5 后台 AI Memory 写入：低干扰比高吞吐更重要
- background write throttle
- foreground read boost
- idle-time GC
- thermal-aware background scheduling
- power-state aware writeback

### 5.6 Thermal：AI PC 是长时间中高负载，不是短跑
- 更平滑的 thermal throttling 曲线
- 避免突然从 7GB/s 掉到 1GB/s
- 温度接近阈值时优先保证 read latency
- 后台写入主动降速
- 温度恢复后的性能回升策略

### 5.7 Power：NPU 本地 AI 很多是在电池模式下跑
- APST/ASPM 状态切换延迟
- idle power
- burst read 后快速回低功耗
- 低功耗状态下的小随机读唤醒延迟
- Modern Standby 下后台 AI memory 写入

### 5.8 Security：本地隐私 AI 数据会增加 SSD 安全要求
- TCG Opal / Pyrite
- namespace sanitize
- secure erase
- crypto erase
- PLP 或至少 metadata consistency
- power loss 下数据库一致性
- BitLocker 场景性能

---

## 6. AI SSD Benchmark 套件设计

建议定义：**AI-PC Storage Benchmark v0.1**

包括 8 个 workload：

| Workload     | 模拟场景             | 核心指标                  | 主要 I/O               |
| ------------ | ---------------- | --------------------- | -------------------- |
| AI-Load      | 本地模型加载           | load time / TTFT      | 大文件顺序读 + metadata    |
| AI-RAG-Build | 知识库建库            | docs/s / build time   | 小文件读 + 随机写           |
| AI-RAG-Query | 本地语义搜索           | query p95/p99         | 小块随机读                |
| AI-Memory    | Recall-like 后台记忆 | foreground p99        | 后台小写 + 前台读           |
| AI-KV        | SSD KV cache     | TTFT / tokens/s / p99 | 64K~256K random read |
| AI-Creator   | 图片/视频生成          | pipeline time         | 模型读 + 素材读写           |
| AI-CodeAgent | 代码 Agent         | agent step latency    | metadata + 小文件       |
| AI-Multitask | 多任务 QoS          | 前台抖动                  | 混合读写                 |

每个 workload 都要测三种状态：
- Fresh drive
- Aged drive
- Thermal stressed drive

每个状态都测：
- 空盘 20%
- 空盘 50%
- 空盘 80%
- 空盘 90%

---

## 7. 具体 fio pattern 建议

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

---

## 8. Firmware 优化优先级排序

### P0：必须做
1. Mixed read/write 下 read p99 latency 优化
2. 64K~256K random read profile
3. 低 QD 顺序读稳定性
4. thermal throttling 平滑化
5. aged drive 下 QoS
6. BitLocker / flush / FUA latency 测试

### P1：AI PC 强相关
1. RAG / SQLite / DuckDB / vector DB workload profile
2. 后台写入不影响前台读
3. host stream hint / temperature-aware GC
4. 模型 shard 多文件读取优化
5. HMB mapping cache 策略优化

### P2：高级 AI SSD 差异化
1. KV cache read priority mode
2. AI workload detection
3. namespace / stream isolation
4. DirectStorage / GPU storage path 适配
5. Smart prefetch for model file layout
6. AI data secure erase / crypto erase workflow

---

## 核心结论

AI PC 对 SSD 的要求从过去的：
- 开机快
- 游戏加载快
- 大文件拷贝快

变成：
- 本地模型加载快
- RAG 检索 p99 低
- 后台 AI memory 不拖慢前台
- 长上下文 KV cache 不爆尾延迟
- 模型/向量库/快照长期占盘后仍稳定
- 加密和低功耗下性能不崩

**固件优化的核心方向：从"峰值吞吐优先"转向"AI 前台读延迟、混合负载 QoS、长时间温控、隐私数据一致性优先"。**

---

## 参考资料

- [Introducing Copilot+ PCs - The Official Microsoft Blog](https://blogs.microsoft.com/blog/2024/05/20/introducing-copilot-pcs/)
- [Retrace your steps with Recall - Microsoft Support](https://support.microsoft.com/en-us/windows/retrace-your-steps-with-recall-aa03f8a0-a78b-4b3e-b0a1-2eb8ac48701c)
- [Phison extends aiDAPTIV+ to boost AI inference on PCs](https://www.blocksandfiles.com/ai-ml/2026/01/07/phison-extends-aidaptiv-to-boost-ai-inference-on-pcs/)
- [Procyon AI Computer Vision Benchmark - UL](https://benchmarks.ul.com/procyon/ai-computer-vision)
- [Overview of PCMark 10 Storage benchmarks](https://support.benchmarks.ul.com/support/solutions/articles/44002171443-overview-of-pcmark-10-storage-benchmarks)
- [Samsung Electronics Presents Vision for AI Memory and Storage](https://semiconductor.samsung.com/news-events/tech-blog/samsung-electronics-presents-vision-for-ai-memory-and-storage-at-fms-2025/)
