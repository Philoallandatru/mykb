---
type: concept
category: 系统实现
source: llama.cpp技术深度解析
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - memory-management
  - llama-cpp
  - mmap
  - file-io
---

# mmap在llama.cpp中的应用

## 💡 定义

llama.cpp中的mmap是用来把**GGUF模型文件映射到进程虚拟地址空间**的技术，让操作系统按需把模型权重页从存储加载到内存。

## 📝 详细说明

### 核心作用

> **让操作系统按需把模型文件的权重页从SSD/HDD加载到内存，而不是llama.cpp一开始用read()把整个模型完整读进一块私有RAM。**

### 不是什么

**常见误解** ❌:
- ❌ 不是"把模型直接加载到显存"
- ❌ 不是"CPU offload"
- ❌ 不是"让SSD直接参与计算"
- ❌ 不是"保证低RAM占用"
- ❌ 不是"GPU offload"

**真实作用** ✅:
```
GGUF模型文件 → 进程虚拟内存映射 → OS按需加载模型页
```

### 工作原理

**传统方式 (不用mmap)**:
```
GGUF模型文件
  ↓ read()
llama.cpp自己分配RAM buffer
  ↓
把模型权重读进RAM
  ↓
CPU/GPU后端使用这些权重
```

**使用mmap**:
```
GGUF模型文件
  ↓ mmap / CreateFileMapping
进程虚拟地址空间
  ↓ page fault时按需读取
OS page cache / 物理内存
```

**关键机制**: 文件I/O伪装成内存访问

## 🔗 相关概念

- [[cpu-offload|CPU Offload]]
- [[gpu-memory|GPU内存管理]]
- [[page-cache|操作系统页缓存]]
- [[virtual-memory|虚拟内存]]
- [[gguf-format|GGUF格式]]

## 💼 解决的核心问题

### 1. 加快模型启动

**不用mmap**:
```
先读完整模型 → 再开始初始化
启动时间: 长
```

**用mmap**:
```
建立映射 → 需要哪些页再读哪些页
启动时间: 短
```

**收益**: 启动阶段更快，不需要等待完整读取

### 2. 利用操作系统Page Cache

**第一次运行**:
```
SSD → RAM page cache → llama.cpp使用
速度: 慢
```

**第二次运行同一模型** (page cache未回收):
```
RAM page cache → llama.cpp使用
速度: 快
```

**现象**:
```
第一次加载慢
第二次加载很快
```

这不是llama.cpp自己缓存，而是OS缓存了文件页。

### 3. 减少一份额外拷贝

**不用mmap**:
```
SSD → OS page cache → llama.cpp私有buffer
(两份内存占用)
```

**用mmap**:
```
SSD → OS page cache / file-backed pages → llama.cpp直接访问
(共享内存)
```

**收益**: 减少用户态buffer拷贝

## 🎯 mmap vs --no-mmap

### 对比表

| 模式 | 行为 | 优点 | 缺点 |
|------|------|------|------|
| 默认mmap | 模型文件映射到虚拟地址空间，按需加载 | 启动快、少拷贝、利用OS cache | RAM紧张时page fault/pageout |
| `--no-mmap` | 不使用内存映射，显式读入内存 | 内存行为更直接、少受page cache影响 | 加载慢，需要足够RAM |

### 特点对比

**mmap模式**:
```
让OS管模型页什么时候进RAM、什么时候被回收
```

**--no-mmap模式**:
```
llama.cpp更主动地把模型读进自己管理的内存
```

### 使用建议

**默认开mmap通常合理** ✅:
```
1. 模型文件在本地NVMe SSD
2. RAM比较充足
3. 希望模型启动快
4. 经常重复加载同一模型
5. 希望利用OS page cache
```

**考虑--no-mmap** ⚠️:
```
1. mmap导致page cache占用异常
2. 希望内存占用更可控
3. 有足够RAM完整装下模型
4. 某些backend/MoE模型兼容问题
5. 避免运行中page fault抖动
```

**警告**: 
> `--no-mmap`不会减少模型本身需要的内存，只是改变加载和管理方式。RAM不够时可能更容易OOM。

## 🔧 与其他技术的关系

### mmap与GPU Offload

**示例命令**:
```bash
llama-server -m model.gguf -ngl 99
```

**工作流程**:
```
模型文件通过mmap映射
  ↓
部分或全部layer被拷贝/上传到GPU VRAM
  ↓
GPU执行这些layer
```

**职责分工**:
```
mmap: 负责模型文件如何从磁盘进入地址空间
-ngl/--gpu-layers: 负责哪些layer放到GPU
```

两者不是同一概念，是互补关系。

### 全GPU offload时RAM占用

**疑问**: 为什么全GPU offload时RAM还有占用？

**原因**:
```
1. GGUF文件仍被mmap到进程地址空间
2. OS page cache缓存了模型文件
3. 部分tensor/metadata/tokenizer/buffer仍在RAM
4. KV cache可能在RAM或VRAM
5. OS统计file-backed memory的方式复杂
```

**结论**: 不是重复加载，是mmap + page cache + runtime buffer的组合

### mmap与mlock

**mmap**: 映射文件，OS可回收页
```
按需映射，OS可回收
```

**mmap + mlock**: 锁定在RAM，减少page fault
```
映射后尽量锁在RAM，减少page fault
```

**--no-mmap**: 不走文件映射
```
直接加载到普通内存
```

**mlock的使用**:
- RAM充足: `--mlock`减少运行中卡顿
- RAM不足: `--mlock`可能直接内存不足

## 📊 性能影响

### 对SSD的影响

**第一次加载模型**:
```
大量顺序读/半顺序读
SSD I/O密集
```

**运行过程 (RAM充足)**:
```
模型页大部分留在RAM
SSD I/O很少
性能良好
```

**运行过程 (RAM不足)** ⚠️:
```
频繁page fault
SSD被反复读取
tokens/s急剧下降
系统卡顿
```

这是**page thrashing**:
```
访问layer A → 从SSD读入
访问layer B → 从SSD读入，A被挤掉
下一轮又访问A → 再从SSD读入
(恶性循环)
```

### 性能场景分析

**场景A: 模型大部分在VRAM** ✅
```
mmap负责加载
GPU layer上传到VRAM
RAM主要保留metadata/page cache/少量CPU tensor
```
表现: 正常，性能好

**场景B: RAM不够，频繁回收** ❌
```
访问模型页 → 从SSD page-in
内存压力大 → 被回收
下一轮 → 又page-in
```
表现: SSD占用高、CPU wait高、tokens/s下降

## 💡 实际应用

### 配置示例

**基础使用**:
```bash
# 默认使用mmap
llama-server -m model.gguf

# 禁用mmap
llama-server -m model.gguf --no-mmap

# mmap + mlock (锁定在RAM)
llama-server -m model.gguf --mlock
```

**GPU offload组合**:
```bash
# mmap + 部分GPU
llama-server -m model.gguf -ngl 20

# mmap + 全GPU
llama-server -m model.gguf -ngl 99

# 禁用mmap + GPU
llama-server -m model.gguf --no-mmap -ngl 40
```

### 内存监控

**检查mmap效果**:
```bash
# Linux - 查看进程内存映射
pmap -x <pid>

# 查看page cache使用
free -h

# 查看swap使用
swapon --show
vmstat 1
```

**正常状态**:
- 进程RSS适中
- Page cache较大
- Swap使用为0或很小

**异常状态** (page thrashing):
- Page cache频繁波动
- Swap in/out活跃
- SSD I/O持续高
- CPU wait增加

## ⚠️ 常见陷阱

### 陷阱1: 低RAM环境强行mmap大模型

**场景**:
```
可用RAM: 8GB
模型大小: 20GB
GPU offload: 部分
```

**结果**: Page thrashing，性能灾难

**解决**:
- 增加GPU offload层数
- 使用更小的量化模型
- 增加系统RAM
- 考虑--no-mmap (但可能无法启动)

### 陷阱2: 误以为mmap减少内存占用

**误解**: 
> 用mmap可以让大模型在小RAM上运行

**现实**:
> mmap只是改变加载方式，模型仍需要内存空间。RAM不足时只会导致page thrashing。

### 陷阱3: 混淆mmap与GPU/CPU offload

**mmap**: 文件到内存的映射机制
**GPU offload**: 把计算和数据放到GPU
**CPU offload**: 把GPU数据临时放CPU DRAM

三者是不同层面的技术。

## 📚 参考资料

- [[cpu-offload|CPU Offload]] - 内存管理策略
- [[gpu-direct-storage|GPU Direct Storage]] - 另一种I/O优化
- [[vllm-vs-sglang|vLLM vs SGLang]] - 企业级serving方案

## 💭 个人理解

### 核心价值

mmap是一个**优雅的工程折衷**:
```
不用mmap: 
  - 启动慢
  - 需要大量RAM
  + 性能可预测

用mmap:
  + 启动快
  + 利用OS缓存
  - 依赖OS内存管理
  - RAM不足时可能抖动
```

### 适用场景

**mmap非常适合**:
- 开发/测试环境频繁重启模型
- RAM充足的系统
- NVMe SSD + 现代OS
- 需要快速启动

**mmap不适合**:
- RAM严重不足
- 对性能稳定性要求极高
- 已经在用[[cpu-offload|CPU offload]]或[[gpu-direct-storage|GDS]]等机制

### 与LLM serving的关系

**本地推理** (llama.cpp):
- mmap是默认且推荐的方式
- 简单有效

**生产环境** ([[vllm|vLLM]]/[[sglang|SGLang]]):
- 通常不用mmap
- 自己管理内存和KV cache
- 更复杂但更可控

---

*创建于: 2026-06-04*
*来源: llama.cpp技术深度分析*
