# AI SSD

## 核心定义

**AI SSD 不是"SSD 里塞一个 AI 芯片"，而是面向 AI PC 本地推理、RAG、向量索引、KV Cache、模型加载、多模态内容处理、隐私数据检索等场景，对读延迟、随机小块、并发 QoS、温控、掉电一致性、安全擦除/加密做专门优化的 SSD。**

## 背景趋势

AI PC 已成为明确趋势：
- **Copilot+ PC**：40+ TOPS NPU 作为关键门槛
- **微软 Foundry Local**：推动 LLM 直接在 Windows 设备本地运行
- **Recall 功能**：快照和上下文信息保存在本地硬盘并加密
- **行业宣传**：SSD 作为本地 AI 的容量扩展、KV cache、训练/微调辅助层

## 六大核心场景

### 1. 本地 LLM 模型加载/切换
- 4GB ~ 80GB 模型文件从 SSD 加载到 DRAM/VRAM/NPU
- 关键指标：模型首次可用时间、TTFT、模型切换时间
- I/O 特征：大文件顺序读 + metadata 小文件随机读

### 2. 本地 RAG / 个人知识库
- PDF/Word/邮件等文档 → OCR/chunk/embedding → 向量库存到 SSD
- 关键指标：query latency p99、建库时间、检索时间
- I/O 特征：索引构建时大量小文件读写，查询时小块随机读

### 3. Windows Recall / AI Memory
- 周期性屏幕快照 → OCR/embedding → 本地加密数据库
- 关键指标：后台写入对前台的影响、加密场景 p99 latency
- I/O 特征：后台持续小写入 + 前台搜索随机读

### 4. SSD 作为 KV Cache / Memory Extension
- 长上下文 LLM 把部分 KV Cache 放到 SSD
- 关键指标：TTFT、tokens/s、GPU/NPU bubble time
- I/O 特征：64KB~256KB 小块随机读，p99 latency 比平均带宽更重要

### 5. 多模态内容创作
- Stable Diffusion / 视频生成 / Whisper / 图像编辑
- 关键指标：模型加载时间、生成 pipeline 时间
- I/O 特征：模型大文件顺序读 + 素材随机读 + 中间缓存写入

### 6. AI 开发者工作流
- VS Code / Cursor / Copilot / Claude Code
- 关键指标：首次打开 repo 时间、Agent 单步延迟
- I/O 特征：大量小文件 metadata 操作 + 编译产物 burst write

## 性能要求转变

### 传统 SSD 重点
- 开机快
- 游戏加载快
- 大文件拷贝快
- CrystalDiskMark 峰值带宽

### AI SSD 新重点
- **本地模型加载快**
- **RAG 检索 p99 低**
- **后台 AI memory 不拖慢前台**
- **长上下文 KV cache 不爆尾延迟**
- **模型/向量库/快照长期占盘后仍稳定**
- **加密和低功耗下性能不崩**

## 固件优化核心方向

**从"峰值吞吐优先"转向"AI 前台读延迟、混合负载 QoS、长时间温控、隐私数据一致性优先"**

### 三个优化优先级

**P0 必须做：**
1. Mixed read/write 下 read p99 latency 优化
2. 64K~256K random read profile（不只是 4K）
3. 低 QD 顺序读稳定性
4. thermal throttling 平滑化
5. aged drive 下 QoS
6. BitLocker / flush / FUA latency 测试

**P1 AI PC 强相关：**
1. RAG / SQLite / DuckDB / vector DB workload profile
2. 后台写入不影响前台读
3. host stream hint / temperature-aware GC
4. 模型 shard 多文件读取优化
5. HMB mapping cache 策略优化

**P2 高级差异化：**
1. KV cache read priority mode
2. AI workload detection
3. namespace / stream isolation
4. DirectStorage / GPU storage path 适配
5. Smart prefetch for model file layout
6. AI data secure erase / crypto erase workflow

## 关键技术特征

### 读延迟优先
- read-priority arbitration
- short-read fast path
- foreground queue 优先级
- GC 可中断/可让路

### 中等块随机读优化
- 64K/128K/256K random read（KV cache 典型大小）
- read command coalescing
- mapping cache 命中优化

### 温控和功耗
- 平滑 thermal throttling 曲线（避免 7GB/s 突降到 1GB/s）
- 温度接近阈值时优先保证 read latency
- 低功耗状态下小随机读唤醒延迟
- Modern Standby 下后台 AI memory 写入

### 安全性
- TCG Opal / Pyrite
- secure erase / crypto erase
- BitLocker 场景性能
- power loss 下数据库一致性

## 相关概念
- [[vectordb-benchmark]]
- [[mlcommons-storage-benchmark]]
- [[inference-frameworks-ai-ssd]]

- [[kv-cache]] - KV cache 是 AI SSD 的重要应用场景
- [[gpu-direct-storage]] - GPU Direct Storage 可加速模型加载
- [[near-storage-computing]] - Near-storage computing 是更激进的方向
- [[lmcache]] - LMCache 使用 SSD 作为 KV cache 存储层
- [[cpu-offload]] - CPU offload 把数据放在 DRAM，AI SSD 则是 SSD 层

## 参考资料

完整分析见：[[../raw/ai-ssd-comprehensive-analysis|AI SSD 工程化定义与 Benchmark 设计]]

- [Introducing Copilot+ PCs - Microsoft Blog](https://blogs.microsoft.com/blog/2024/05/20/introducing-copilot-pcs/)
- [Phison aiDAPTIV+ for PC AI inference](https://www.blocksandfiles.com/ai-ml/2026/01/07/phison-extends-aidaptiv-to-boost-ai-inference-on-pcs/)
- [Samsung AI Memory and Storage Vision](https://semiconductor.samsung.com/news-events/tech-blog/samsung-electronics-presents-vision-for-ai-memory-and-storage-at-fms-2025/)

---

**标签**: #storage #ai-pc #ssd #optimization #benchmark
