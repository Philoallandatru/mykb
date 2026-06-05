# KV Cache Benchmark IO Profiling 学习笔记

## 核心洞察

KV Cache 基准测试框架已经内置了**完整的 IO profiling 能力**，涵盖从操作级追踪到实时监控、从用户空间到内核空间的全栈分析。理解这些工具的设计思想和使用场景，可以避免重复造轮，并快速定位性能瓶颈。

---

## 1. 四层 Profiling 架构的设计智慧

KV Cache benchmark 的 profiling 设计采用了**分层架构**，每层解决不同粒度的问题：

| 层级 | 工具 | 粒度 | 开销 | 适用场景 |
|------|------|------|------|---------|
| **应用层** | IOTracer | 操作级 | 1-2% | 详细分析每个IO操作 |
| **监控层** | StorageMonitor | 秒级聚合 | <0.5% | 实时性能监控 |
| **内核层** | bpftrace | 块设备级 | 1-3% | 内核调试和验证 |
| **后端层** | IOTiming | 函数级 | <0.1% | 延迟分解和优化 |

**Why**: 单一工具无法同时满足"详细追踪"和"低开销"的需求。分层设计让用户根据场景选择合适的工具组合。

**How to apply**: 
- 开发调试：启用所有层级，获取最详细的信息
- 性能测试：只启用 StorageMonitor（自动启用），最小化干扰
- 生产排查：启用 IOTracer，但不启用内核追踪

---

## 2. IOTracer：操作级追踪的关键设计

### 核心特性

**压缩存储**：
- 使用 zstd 压缩，10-20× 压缩比
- `.csv.zst` 扩展名自动识别
- 压缩级别 3：平衡速度和压缩率

**结构化数据**：
```csv
Timestamp,Operation,Object_Size_Bytes,Tier,Key,Phase
1717477933.245,prefill_write,8388608,NVMe,user_1_layer_0,prefill
```

**Why**: 
1. **CSV 格式易于后处理** - pandas/Excel/数据库都能直接读取
2. **zstd 压缩降低存储开销** - 长时间测试不会产生巨大文件
3. **时间戳精确到微秒** - 可以分析突发和周期性模式
4. **包含 Key 和 Phase** - 可以追踪单个用户的IO路径

**How to apply**:
```bash
# 启用操作级追踪
python3 kv-cache.py \
  --io-trace-log trace.csv.zst \
  --model mistral-7b \
  --num-users 50 \
  --duration 180
```

**后处理示例**:
```python
import pandas as pd
df = pd.read_csv('trace.csv')

# 找到最大的IO操作
print(df.nlargest(10, 'Object_Size_Bytes'))

# 分析 prefill vs decode 的IO模式
prefill = df[df['Operation'].str.contains('prefill')]
decode = df[df['Operation'].str.contains('decode')]
print(f"Prefill avg size: {prefill['Object_Size_Bytes'].mean()}")
print(f"Decode avg size: {decode['Object_Size_Bytes'].mean()}")

# 时间序列分析
df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
df.set_index('Timestamp').resample('1S')['Object_Size_Bytes'].sum().plot()
```

---

## 3. StorageMonitor：实时监控的自动化设计

### 关键洞察

**自动启用，零配置**：
- 不需要任何CLI参数
- 自动在后台采样（100ms间隔）
- 结果自动包含在 JSON 输出中

**分层统计**：
- 分别统计 GPU、CPU、NVMe 三个 tier
- 可以清楚看到各层的吞吐量和延迟
- 发现瓶颈层级

**关键指标**：
- `throughput_gibs`: 实际达到的吞吐量
- `iops`: 每秒操作数
- `latency_p95_ms`: 95 百分位延迟（不是平均值！）
- `queue_depth`: 并发请求数
- `saturation`: 饱和度（队列深度 / 目标并发）

**Why**:
1. **p95 比平均值更重要** - 长尾延迟影响用户体验
2. **自动启用避免遗忘** - 用户不需要记住开启监控
3. **100ms 采样平衡精度和开销** - 太频繁会影响性能，太稀疏会丢失细节
4. **分层统计快速定位瓶颈** - 看哪一层的 saturation 最高

**How to apply**:
```python
# 从 results.json 读取监控数据
import json
with open('results.json') as f:
    results = json.load(f)
    
monitoring = results['monitoring']
print(f"Avg throughput: {sum(monitoring['throughput_gibs'])/len(monitoring['throughput_gibs']):.2f} GiB/s")
print(f"Avg IOPS: {sum(monitoring['iops'])/len(monitoring['iops']):.0f}")
print(f"p95 latency: {max(monitoring['latency_p95_ms']):.2f} ms")

# 找到性能下降的时间点
import matplotlib.pyplot as plt
plt.plot(monitoring['throughput_gibs'])
plt.xlabel('Time (seconds)')
plt.ylabel('Throughput (GiB/s)')
plt.show()
```

---

## 4. bpftrace：内核级追踪的威力与代价

### 功能

使用 eBPF 追踪内核块设备层的 IO 延迟：
- `block:block_rq_issue`: 请求发出时间
- `block:block_rq_complete`: 请求完成时间
- 延迟分布直方图（微秒级）

### 适用场景

**何时使用**：
- ✅ 怀疑内核调度问题
- ✅ 验证 SSD firmware 延迟
- ✅ 对比不同内核版本
- ✅ 分析 IO 队列深度影响

**何时不用**：
- ❌ 常规性能测试（StorageMonitor 足够）
- ❌ 生产环境（需要 sudo 权限）
- ❌ 长时间运行（1-3% CPU 开销累积）

**Why**:
1. **内核追踪是真相的最后一层** - 用户空间的计时可能被调度延迟干扰
2. **需要 sudo 权限限制了使用场景** - 不能在所有环境运行
3. **eBPF 开销虽小但累积** - 长时间运行会影响性能

**How to apply**:
```bash
# 仅在需要验证内核行为时启用
sudo python3 kv-cache.py \
  --enable-latency-tracing \
  --model mistral-7b \
  --num-users 50 \
  --duration 60  # 短时间测试

# 分析输出的直方图
# 看延迟分布是否符合预期
```

---

## 5. IOTiming：延迟分解的精细化分析

### 延迟组成

```python
IOTiming(
    total=0.0045,     # 4.5ms 总延迟
    device=0.0042,    # 4.2ms 设备延迟 (93%)
    host=0.0003,      # 0.3ms 主机处理 (7%)
)
```

**三个延迟组件**：
1. **total**: 端到端延迟（用户感知）
2. **device**: 块设备IO时间（SSD真实延迟）
3. **host**: 主机处理时间（CPU、序列化、解压）

### 关键洞察

**定位瓶颈**：
- `device_pct > 90%` → SSD 是瓶颈，考虑更快的 SSD 或优化 IO pattern
- `host_pct > 30%` → CPU 处理是瓶颈，考虑优化序列化、减少拷贝
- `host_pct > 50%` → 严重的主机瓶颈，检查是否有不必要的计算

**优化方向**：
```python
# 高 device 延迟 → 优化存储层
- 使用更快的 NVMe SSD
- 减少随机 IO，增加顺序性
- 调整 IO 大小（避免过小或过大）

# 高 host 延迟 → 优化处理层
- 使用零拷贝技术
- 优化序列化算法（msgpack/protobuf）
- 减少压缩/解压开销
- 使用 direct IO 绕过 page cache
```

**Why**:
1. **分解延迟才能精确优化** - 不分解就不知道瓶颈在哪
2. **device vs host 是两个完全不同的优化方向** - 优化错了方向浪费时间
3. **百分比比绝对值更有指导意义** - 优化占比高的部分收益最大

**How to apply**:
```python
# 在后端实现中记录 IOTiming
def read(self, key: str) -> Tuple[bytes, IOTiming]:
    device_start = time.perf_counter()
    raw_data = self._read_from_disk(key)
    device_time = time.perf_counter() - device_start
    
    host_start = time.perf_counter()
    decompressed = zstd.decompress(raw_data)
    deserialized = msgpack.unpackb(decompressed)
    host_time = time.perf_counter() - host_start
    
    return deserialized, IOTiming(
        total=device_time + host_time,
        device=device_time,
        host=host_time,
    )

# 分析 IOTiming 数据
timings = [backend.read(key)[1] for key in keys]
avg_device_pct = sum(t.device_pct for t in timings) / len(timings)
print(f"Device latency: {avg_device_pct:.1f}%")
if avg_device_pct > 90:
    print("Bottleneck: SSD performance")
else:
    print("Bottleneck: Host processing")
```

---

## 6. 性能开销对比：选择合适的工具组合

### 开销量化

| 工具 | CPU 开销 | 存储开销 | 内存开销 | 延迟影响 |
|------|---------|---------|---------|---------|
| IOTracer | 1-2% | 中（压缩后） | 低 | <1% |
| StorageMonitor | <0.5% | 低 | 低 | <0.1% |
| bpftrace | 1-3% | 低 | 中 | ~1% |
| IOTiming | <0.1% | 无 | 无 | <0.01% |
| log-level DEBUG | 5-10% | 高 | 低 | 2-5% |

### 场景推荐

**开发调试（最详细）**：
```bash
--io-trace-log trace.csv.zst \
--enable-latency-tracing \
--log-level DEBUG
```
总开销：~8-15%，但获取完整信息

**性能基准测试（最小干扰）**：
```bash
--log-level INFO
# 不启用 --io-trace-log
# 不启用 --enable-latency-tracing
# StorageMonitor 自动启用
```
总开销：<0.5%，不影响测试结果

**生产环境排查（平衡）**：
```bash
--io-trace-log trace.csv.zst \
--log-level WARNING
# 不启用 --enable-latency-tracing
```
总开销：~2%，可接受且有详细追踪

**Why**:
1. **开发时可以容忍 10% 开销** - 详细信息更重要
2. **性能测试不能有 >1% 干扰** - 会影响基准测试的准确性
3. **生产环境需要平衡** - 既要排查问题，又不能拖垮系统

---

## 7. 后处理分析：从数据到洞察

### Trace 数据分析模式

#### 模式 1：按操作类型统计
```python
import pandas as pd
df = pd.read_csv('trace.csv')

# 各操作类型的统计
ops_stats = df.groupby('Operation')['Object_Size_Bytes'].agg([
    ('count', 'count'),
    ('total_bytes', 'sum'),
    ('avg_size', 'mean'),
    ('p95_size', lambda x: x.quantile(0.95))
])
print(ops_stats)
```

**洞察**：
- `prefill_write` 平均大小 >> `decode_write` → prefill 是大块 IO
- `evict` 次数多 → cache 容量不够
- `prefill_read` / `prefill_write` 比例 → cache hit rate

#### 模式 2：按层级统计
```python
# 各层级的总流量
tier_traffic = df.groupby('Tier')['Object_Size_Bytes'].sum() / (1024**3)
print(f"GPU traffic: {tier_traffic.get('GPU', 0):.2f} GiB")
print(f"CPU traffic: {tier_traffic.get('CPU', 0):.2f} GiB")
print(f"NVMe traffic: {tier_traffic.get('NVMe', 0):.2f} GiB")
```

**洞察**：
- NVMe 流量 >> GPU 流量 → 大部分 cache miss 到了 SSD
- CPU 流量高 → 中间层 cache 有效工作
- GPU 流量低 → GPU cache 太小或 workload 不适合 cache

#### 模式 3：时间序列分析
```python
# 吞吐量随时间变化
df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
throughput = df.set_index('Timestamp').resample('1S')['Object_Size_Bytes'].sum() / (1024**3)

import matplotlib.pyplot as plt
throughput.plot()
plt.xlabel('Time')
plt.ylabel('Throughput (GiB/s)')
plt.title('I/O Throughput Over Time')
plt.show()
```

**洞察**：
- 吞吐量周期性波动 → prefill/decode 交替
- 吞吐量逐渐下降 → thermal throttling 或 cache 污染
- 吞吐量突然下降 → GC 触发

#### 模式 4：单用户 IO 路径追踪
```python
# 追踪某个用户的所有 IO
user_trace = df[df['Key'].str.contains('user_1')]
print(user_trace[['Timestamp', 'Operation', 'Tier', 'Phase']])
```

**洞察**：
- prefill 先写后读 → write-through cache
- decode 只读不写 → read-only cache
- 跨层级跳转频繁 → cache miss 多

---

## 8. 设计原则总结

### 原则 1：分层设计，各司其职
不同粒度的问题需要不同粒度的工具。IOTracer 记录详细信息，StorageMonitor 提供宏观视角。

### 原则 2：自动化优于手动
StorageMonitor 自动启用，用户不需要记住开启。减少人为错误。

### 原则 3：开销透明化
文档明确标注每个工具的开销，让用户根据场景选择。

### 原则 4：结构化输出
CSV/JSON 格式便于机器和人类处理，避免非结构化日志。

### 原则 5：压缩降低成本
zstd 压缩让长时间追踪成为可能，不会产生 TB 级文件。

### 原则 6：延迟分解指导优化
IOTiming 区分 device 和 host，精确定位瓶颈。

### 原则 7：权限分级
bpftrace 需要 sudo，其他工具不需要。让大部分功能在受限环境也能用。

---

## 9. 实战案例：定位 SSD 性能瓶颈

### 场景
KV cache benchmark 测试中发现 TTFT 很高，怀疑是 SSD 延迟问题。

### Step 1：启用完整 profiling
```bash
python3 kv-cache.py \
  --model mistral-7b \
  --num-users 50 \
  --duration 180 \
  --io-trace-log trace.csv.zst \
  --enable-latency-tracing \
  --log-level DEBUG \
  --output results.json
```

### Step 2：查看 StorageMonitor 数据
```python
import json
with open('results.json') as f:
    results = json.load(f)
    
latency_p95 = results['monitoring']['latency_p95_ms']
print(f"Max p95 latency: {max(latency_p95):.2f} ms")
# 输出: Max p95 latency: 42.5 ms  <- 太高了！
```

### Step 3：分析 IOTracer 数据
```python
import pandas as pd
df = pd.read_csv('trace.csv')

# 找到大延迟操作
df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
df['Time_Delta'] = df['Timestamp'].diff().dt.total_seconds() * 1000  # ms

slow_ops = df[df['Time_Delta'] > 40]  # >40ms
print(slow_ops[['Operation', 'Object_Size_Bytes', 'Tier', 'Time_Delta']])
# 发现大部分是 NVMe 层的 256KB 随机读
```

### Step 4：检查 IOTiming 分解
```python
# 从日志中提取 IOTiming（假设后端记录了）
# 发现 device_pct = 95%
# 说明瓶颈在 SSD，不是主机处理
```

### Step 5：验证内核行为
```bash
# bpftrace 输出显示块设备延迟分布
# 证实 SSD 本身延迟就是 40ms+
```

### 结论
**瓶颈在 SSD 的 256KB 随机读性能**，不是软件问题。

### 解决方案
1. 更换更快的 SSD（PCIe Gen4 → Gen5）
2. 调整 IO 大小（256KB → 64KB，减少单次延迟）
3. 增加并发度（overlap compute and IO）
4. 使用 io_uring 的 batching 功能

---

## 10. 与 AI SSD Benchmark 的关联

### 知识迁移

KV Cache benchmark 的 profiling 架构可以直接应用到 [[ai-ssd-benchmark-design|AI SSD Benchmark]] 设计中：

**Layer 2（AI I/O Pattern Benchmark）**：
- 使用 IOTracer 记录 fio 无法模拟的真实应用 IO pattern
- 使用 StorageMonitor 验证 fio 结果的真实性

**Layer 3（Application Benchmark）**：
- 使用 IOTracer 追踪 RAG query、模型加载的详细 IO
- 使用 IOTiming 分解延迟，区分 SSD 和主机瓶颈

**Layer 4（Stress Benchmark）**：
- 使用 bpftrace 验证 thermal throttling 是否影响内核延迟
- 使用 StorageMonitor 监控长时间测试的性能衰减

### 工具复用

```python
# 在 AI SSD Benchmark 中使用相同的 IOTracer
from kv_cache.tracer import IOTracer

with IOTracer("ai-ssd-trace.csv.zst") as tracer:
    # 测试模型加载
    tracer.record("model_load", model_size_bytes, "NVMe", "llama-3-8b")
    
    # 测试 RAG query
    tracer.record("rag_query", chunk_size_bytes, "NVMe", "doc_chunk_42")
```

---

## 核心结论

KV Cache Benchmark 的 IO profiling 设计体现了**分层架构、自动化、低开销、结构化输出**的最佳实践。

关键takeaway：
1. **分层设计满足不同场景** - 操作级、秒级、内核级、函数级
2. **自动化减少人为错误** - StorageMonitor 默认启用
3. **开销透明化指导选择** - 清楚标注每个工具的开销
4. **延迟分解精确定位** - device vs host 是不同的优化方向
5. **结构化输出便于分析** - CSV/JSON 而非非结构化日志
6. **压缩降低存储成本** - zstd 让长时间追踪成为可能

这套方法论可以直接迁移到 AI SSD Benchmark 和其他存储性能测试场景。

## 相关概念

- [[kv-cache]] - KV cache 的核心概念
- [[ai-ssd-benchmark-design]] - AI SSD benchmark 设计方法论
- [[io-uring]] - 异步 IO 机制
- [[lmcache]] - 使用这套 benchmark 测试的系统

---

**标签**: #learning #benchmark #profiling #io-tracing #performance #kv-cache

