---
type: concept
category: 系统架构
source: AI系统实践经验
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - offloading
  - memory-management
  - gpu
  - cpu
---

# CPU Offload

## 💡 定义

CPU offload是指将原本应存储在GPU HBM/VRAM中的数据迁移到主机侧的CPU DRAM/系统内存中，作为GPU显存的扩展层。

## 📝 详细说明

### 基本流程

```
GPU HBM / VRAM
  ↓ CPU offload
Host DRAM / System RAM
```

**关键理解**: 
- "CPU offload"中的"CPU"主要指CPU侧的DRAM
- **不一定意味着CPU执行计算**

### 三种典型情况

#### 情况1: 数据在CPU DRAM，计算仍在GPU ⭐

**最常见的形式**:

```
权重/KV cache/optimizer state暂存在CPU DRAM
  ↓
需要时通过PCIe拷回GPU
  ↓
GPU执行计算
```

**CPU DRAM角色**: 容量扩展层

**典型场景**:
```
GPU显存: 16GB
模型权重: 24GB
  ↓
部分权重放在系统内存
  ↓
每层计算前把对应权重搬到GPU
```

**优点**:
- ✅ 能跑更大的模型
- ✅ 利用廉价的系统内存

**缺点**:
- ❌ PCIe带宽和延迟成为瓶颈
- ❌ tokens/s通常明显下降
- ❌ 频繁数据传输增加能耗

#### 情况2: CPU-GPU Hybrid计算

**真正的CPU参与计算**:

```
部分attention compute在CPU上做
部分KV cache留在CPU DRAM
GPU做主要矩阵计算
CPU做辅助attention/cache lookup/routing
```

**特点**:
- 不只是数据临时放CPU内存
- 把一部分计算任务也转移到CPU
- 需要更复杂的调度和同步

**代表系统**:
- [[neo|NEO]]
- [[hybridgen|HybridGen]]
- [[apex|APEX]]

#### 情况3: 被动Swap到SSD (危险！)

**问题场景**:
```
GPU数据offload到CPU DRAM
  ↓
CPU DRAM不够
  ↓
OS swap到SSD (被动发生)
```

**结果**:
```
GPU → DRAM → SSD (意外的多层跳转)
```

**危害**:
- ❌ 性能极差
- ❌ 不是框架主动设计的NVMe offload
- ❌ OS被动swap，无优化
- ❌ 可能导致进程假死

**避免方法**:
> CPU offload不要超过可用系统内存

## 🔗 相关概念

- [[gpu-offload|GPU Offload]]
- [[nvme-offload|NVMe/SSD Offload]]
- [[memory-hierarchy|内存层次结构]]
- [[kv-cache|KV缓存]]
- [[pcie-bandwidth|PCIe带宽]]

## 💼 与其他Offload的对比

### 层级关系

```
GPU HBM/VRAM (最快)
  ↓
CPU DRAM / Host RAM  ← CPU offload
  ↓
NVMe SSD / Disk      ← Disk/NVMe offload
  ↓
Remote Storage       ← Network offload
```

### 性能对比表

| 层级 | 延迟 | 带宽 | 容量 | 典型用途 |
|------|------|------|------|---------|
| GPU HBM/VRAM | 最低 (~10ns) | 最高 (2-5 TB/s) | 小 (40-80GB) | 热权重、当前KV、激活 |
| CPU DRAM | 中等 (~100ns) | 中等 (100-200 GB/s) | 较大 (128-512GB) | 权重offload、KV cache、optimizer |
| NVMe SSD | 高 (~100us) | 较低 (3-7 GB/s) | 最大 (TB级) | 冷KV、模型文件、RAG index |

### 关键区别

**CPU offload**:
- 目标: 系统内存DRAM
- 延迟: 微秒级
- 带宽: PCIe限制 (~16-32 GB/s)
- 用途: 权重、optimizer、活跃KV

**NVMe offload**:
- 目标: SSD
- 延迟: 毫秒级
- 带宽: NVMe限制 (~7 GB/s)
- 用途: 冷KV、历史对话、模型文件

## 🔧 实际应用

### 1. vLLM的CPU Offload

**配置示例**:
```bash
vllm serve model_name --cpu-offload-gb 10
```

**含义**:
```
每张GPU额外借用约10GB CPU内存作为显存扩展
```

**工作机制**:
```
部分模型权重放在CPU RAM
推理时按需搬回GPU
decode阶段频繁访问会受PCIe限制
```

**使用场景**:
- ✅ 模型刚好超过GPU显存一点
- ✅ prefill阶段为主（权重访问少）
- ⚠️ decode阶段会慢（频繁访问权重）

### 2. DeepSpeed的CPU Offload

**ZeRO-Offload**:
```
Optimizer states → CPU DRAM
Gradients → CPU DRAM
参数更新在CPU上做
Forward/backward在GPU上做
```

**适用场景**: 训练大模型，GPU显存不足

### 3. LMCache的KV Cache Offload

**多层配置**:
```yaml
local_cpu: true          # 启用CPU DRAM层
max_local_cpu_size: 5.0  # 5GB CPU DRAM
local_disk: "..."        # 进一步offload到SSD
```

**工作流程**:
```
GPU HBM: 最热KV (当前batch)
CPU DRAM: 热KV (最近使用)
SSD: 冷KV (历史对话)
```

**关键配置陷阱**:
> `local_cpu: true` 只启用CPU层，不是磁盘层！

参见: [[lmcache-stress-test-learning|LMCache实验教训]]

### 4. llama.cpp和Ollama

**n-gpu-layers参数**:
```bash
# 只加载20层到GPU，其余在CPU
ollama run model --n-gpu-layers 20
```

**实际含义**:
```
20层权重在GPU
其余层权重在CPU DRAM
推理时混合使用CPU和GPU计算
```

这是真正的CPU-GPU hybrid inference。

## 🎯 何时使用CPU Offload

### ✅ 适合的场景

1. **模型略大于GPU显存**
   ```
   模型: 24GB
   GPU: 16GB
   CPU RAM: 64GB
     ↓
   CPU offload 8GB
   ```

2. **Prefill为主的workload**
   - 长上下文输入
   - 批处理任务
   - 权重访问次数少

3. **训练场景的optimizer offload**
   - Optimizer states很大
   - 更新频率相对低
   - CPU DRAM够大

4. **多模型切换**
   - 多个模型轮流使用
   - 不活跃模型放CPU DRAM
   - 快速切换

### ❌ 不适合的场景

1. **Decode密集型workload**
   ```
   每个token都要访问权重
     ↓
   PCIe成为严重瓶颈
     ↓
   tokens/s暴跌
   ```

2. **实时交互应用**
   - 延迟敏感
   - PCIe传输增加延迟
   - 用户体验差

3. **系统内存不足**
   ```
   CPU offload > 可用RAM
     ↓
   OS swap到SSD
     ↓
   性能灾难
   ```

4. **高并发推理**
   - 多请求竞争PCIe带宽
   - 相互影响严重

## 📊 性能影响

### PCIe带宽瓶颈

**典型PCIe规格**:
- PCIe 3.0 x16: ~16 GB/s
- PCIe 4.0 x16: ~32 GB/s
- PCIe 5.0 x16: ~64 GB/s

**vs GPU HBM**:
- HBM2e: ~2 TB/s
- HBM3: ~5 TB/s

**差距**: 30-150×

### 实际影响案例

**无offload** (全GPU):
```
tokens/s: 100
延迟: 10ms
```

**CPU offload 50%权重**:
```
tokens/s: 30-50 (降低50-70%)
延迟: 30-50ms (增加3-5×)
```

**取决于**:
- Offload比例
- 权重访问频率
- PCIe代数
- Batch size

### KV Cache Offload的特殊性

**KV cache访问模式**:
```
Prefill: 一次性写入
Decode: 每token读取一次
```

**影响**:
- Prefill阶段: 影响较小
- Decode阶段: 影响显著
- 长序列: 影响更大

**优化策略**:
```
Hot KV: 留GPU
Warm KV: CPU DRAM
Cold KV: SSD
```

## 💡 最佳实践

### 1. 评估是否需要

**问自己**:
```
1. 模型大多少？超GPU显存10%还是50%？
2. 主要workload是什么？Prefill还是decode？
3. 系统内存够吗？至少2×offload量
4. 延迟要求多少？能接受2-5×慢吗？
```

### 2. 合理配置

**经验法则**:
```
CPU offload <= 可用RAM × 0.5
```

**监控指标**:
- GPU利用率（不要太低）
- PCIe带宽使用率
- 系统内存压力
- Swap使用情况（应该为0）

### 3. 与其他技术组合

**量化 + CPU offload**:
```
模型24GB
  ↓ INT8量化
12GB
  ↓ 8GB GPU + 4GB CPU offload
可用！
```

**Paged attention + CPU offload**:
```
KV cache分页管理
按需swap GPU ↔ CPU
```

### 4. 避免常见陷阱

❌ **陷阱1**: 超配系统内存
```
64GB RAM
CPU offload 60GB
  ↓
OS开始swap
  ↓
性能崩溃
```

❌ **陷阱2**: decode密集型workload用CPU offload
```
实时聊天
每token访问权重
  ↓
PCIe成瓶颈
  ↓
用户等待太久
```

❌ **陷阱3**: 混淆CPU offload和NVMe offload
```
配置CPU offload
以为会用SSD
实际只用DRAM
容量还是不够
```

## 🔍 调试和监控

### 确认是否真的在用CPU offload

**检查系统内存使用**:
```bash
# Linux
free -h
watch -n 1 free -h

# 应该看到进程占用大量内存
```

**检查PCIe流量**:
```bash
# 需要工具如nvidia-smi dmon
nvidia-smi dmon -s u

# PCIe tx/rx应该很高
```

**检查是否swap**:
```bash
# Linux
swapon --show
vmstat 1

# si/so列应该为0
```

### 性能profile

**对比测试**:
```python
# 无offload
baseline_tps = benchmark(gpu_only=True)

# 有offload
offload_tps = benchmark(cpu_offload_gb=10)

# 计算开销
overhead = (baseline_tps - offload_tps) / baseline_tps
print(f"CPU offload overhead: {overhead*100:.1f}%")
```

## 📚 参考资料

- [[.raw/llm-offloading-research-2026|Offloading技术综述]]
- [[lmcache|LMCache系统]] - CPU层和Disk层的区别
- [[memory-hierarchy|内存层次结构]]
- [[pcie-bandwidth|PCIe带宽分析]]

## 💭 个人理解

### 核心记忆点

> **CPU offload = 把数据放到主机侧DRAM，需要时再搬回GPU**

### 容易混淆的点

**误解**: CPU offload就是让CPU计算  
**正确**: 通常只是数据放CPU DRAM，计算仍在GPU

**误解**: CPU offload和disk offload差不多  
**正确**: 性能差距巨大（100×延迟，10-100×带宽）

**误解**: CPU offload是免费的容量扩展  
**正确**: 有显著的PCIe传输开销

### 实践建议

1. **首选方案**: 量化模型到GPU显存内
2. **次选方案**: CPU offload少量权重
3. **最后方案**: CPU offload大量数据 + 接受性能下降

---

*创建于: 2026-06-04*
*来源: AI系统实践经验总结*
