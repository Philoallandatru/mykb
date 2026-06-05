# KV Cache 基准测试 - 现有 IO Profiling 功能

本文档总结了 KV Cache 基准测试中**已实现**的 IO profiling 功能，无需重复开发。

## 1. IOTracer - 操作级 IO 追踪

### 功能概述
`IOTracer` 类提供细粒度的 IO 操作追踪，记录每个存储操作的详细信息。

### 数据字段
- **Timestamp**: 操作时间戳（秒）
- **Operation**: 操作类型（`prefill_read`, `prefill_write`, `decode_read`, `decode_write`, `evict`）
- **Object_Size_Bytes**: 对象大小（字节）
- **Tier**: 存储层级（`GPU`=Tier-0, `CPU`=Tier-1, `NVMe`=Tier-2）
- **Key**: 缓存键标识符
- **Phase**: 执行阶段标识

### 使用方法

#### CLI 参数
```bash
python3 kv-cache.py \
  --io-trace-log trace.csv.zst \
  --model mistral-7b \
  --num-users 50 \
  --duration 180
```

#### 压缩支持
- **格式**: zstd 压缩（`.csv.zst` 扩展名）
- **压缩比**: 10-20× 典型压缩比
- **压缩级别**: 默认 3（平衡速度和压缩率）

#### 代码位置
`kv_cache/tracer.py:14-68`

```python
class IOTracer:
    """Trace I/O operations for analysis."""
    
    def __init__(self, path: str, zstd_level: int = 3):
        self.path = path
        self.zstd_level = zstd_level
        self.writer = None
        self.file_handle = None
        
    def record(self, op: str, size_bytes: int, tier: str, 
               key: str = "", phase: str = ""):
        """Record a single I/O operation."""
        self.writer.writerow({
            "Timestamp": time.time(),
            "Operation": op,
            "Object_Size_Bytes": size_bytes,
            "Tier": tier,
            "Key": key,
            "Phase": phase,
        })
```

#### 上下文管理器
```python
with IOTracer("trace.csv.zst") as tracer:
    tracer.record("prefill_write", 8388608, "NVMe", "user_1_layer_0")
```

### 输出示例
```csv
Timestamp,Operation,Object_Size_Bytes,Tier,Key,Phase
1717477933.245,prefill_write,8388608,NVMe,user_1_layer_0,prefill
1717477933.267,prefill_read,8388608,NVMe,user_1_layer_0,prefill
1717477933.289,decode_read,262144,NVMe,user_1_layer_0,decode
```

---

## 2. StorageMonitor - 实时性能监控

### 功能概述
`StorageMonitor` 类提供实时存储性能指标采集，监控系统级和层级级别的性能。

### 监控指标
- **throughput_gibs**: 吞吐量（GiB/s）
- **iops**: 每秒 IO 操作数
- **latency_p95_ms**: 95 百分位延迟（毫秒）
- **queue_depth**: 队列深度（并发请求数）
- **saturation**: 饱和度指标（队列深度 / 目标并发）

### 采样配置
- **采样间隔**: 100ms（默认）
- **聚合周期**: 1 秒统计窗口
- **分层统计**: 分别统计 GPU、CPU、NVMe 三个层级

### 代码位置
`kv_cache/monitoring.py:12-156`

```python
class StorageMonitor:
    """Monitor storage performance in real-time."""
    
    def __init__(self, sampling_interval_ms: int = 100):
        self.sampling_interval = sampling_interval_ms / 1000.0
        self.metrics = defaultdict(lambda: {
            "throughput_gibs": [],
            "iops": [],
            "latency_p95_ms": [],
            "queue_depth": [],
        })
        
    def record_operation(self, tier: str, size_bytes: int, 
                        latency_sec: float):
        """Record a completed I/O operation."""
        with self.lock:
            self.operations[tier].append({
                "size": size_bytes,
                "latency": latency_sec,
                "timestamp": time.time(),
            })
```

### 自动集成
StorageMonitor 在基准测试中**自动启用**，无需额外配置。监控数据包含在 JSON 输出结果中：

```json
{
  "monitoring": {
    "throughput_gibs": [2.34, 2.41, 2.38],
    "iops": [4521, 4678, 4599],
    "latency_p95_ms": [4.2, 4.5, 4.3],
    "queue_depth": [12, 14, 13]
  }
}
```

---

## 3. 设备级延迟追踪

### 功能概述
使用 `bpftrace` 追踪内核块设备层的 IO 延迟，提供设备级性能分析。

### CLI 参数
```bash
python3 kv-cache.py \
  --enable-latency-tracing \
  --model mistral-7b \
  --num-users 50
```

### 系统要求
- **bpftrace**: 必须安装并可执行
- **sudo 权限**: 需要 root 权限访问内核追踪点
- **内核版本**: Linux 4.4+ with eBPF 支持

### 追踪数据
- **block:block_rq_issue**: 块请求发出时间
- **block:block_rq_complete**: 块请求完成时间
- **延迟分布**: 直方图分布（微秒级）

### 代码位置
`kv_cache/cli.py:396-404`

```python
parser.add_argument(
    "--enable-latency-tracing",
    action="store_true",
    help="Enable bpftrace-based device latency tracing (requires sudo)",
)
```

### 注意事项
- 性能开销：约 1-3% CPU 使用率
- 仅在调试和性能分析时启用
- 生产环境不推荐长期开启

---

## 4. 后端延迟追踪

### 功能概述
`StorageBackend.IOTiming` 数据类提供后端操作的延迟分解。

### 延迟组成
- **total**: 总延迟（包含所有组件）
- **device**: 设备 IO 延迟（块设备层）
- **host**: 主机处理延迟（CPU、内存拷贝、序列化）

### 代码位置
`kv_cache/backends.py:28-36`

```python
@dataclass
class IOTiming:
    """Breakdown of I/O latency components."""
    total: float      # Total end-to-end latency (s)
    device: float     # Device I/O time (s)
    host: float       # Host processing time (s)
    
    @property
    def device_pct(self) -> float:
        return (self.device / self.total) * 100 if self.total > 0 else 0
```

### 集成点
所有 StorageBackend 实现（`FileSystemBackend`, `S3Backend`）在 `read()` 和 `write()` 方法中自动记录 IOTiming：

```python
def read(self, key: str) -> Tuple[bytes, IOTiming]:
    start = time.perf_counter()
    data = self._read_impl(key)
    device_time = time.perf_counter() - start
    
    host_start = time.perf_counter()
    # Deserialization, decompression, etc.
    host_time = time.perf_counter() - host_start
    
    return data, IOTiming(
        total=device_time + host_time,
        device=device_time,
        host=host_time,
    )
```

---

## 5. 日志级别控制

### 功能概述
通过 `--log-level` 参数控制 IO 操作的日志详细程度。

### 日志级别
- **DEBUG**: 每个 IO 操作详细日志（性能影响 5-10%）
- **INFO**: 汇总统计和重要事件（默认）
- **WARNING**: 仅警告和错误
- **ERROR**: 仅错误

### 使用方法
```bash
# 详细 IO 日志
python3 kv-cache.py --log-level DEBUG --model mistral-7b --num-users 10

# 生产环境（最小日志）
python3 kv-cache.py --log-level WARNING --model mistral-7b --num-users 50
```

### 代码位置
`kv_cache/cli.py:388-395`

---

## 6. 综合使用示例

### 完整 IO Profiling 配置
```bash
python3 kv-cache.py \
  --model mistral-7b \
  --generation-mode none \
  --num-users 50 \
  --duration 180 \
  --gpu-mem-gb 0 \
  --cpu-mem-gb 0 \
  --cache-dir /mnt/nvme0/kv_cache \
  --storage-capacity-gb 100 \
  --output results.json \
  --io-trace-log trace.csv.zst \
  --enable-latency-tracing \
  --log-level DEBUG \
  --seed 42
```

### 输出文件
1. **results.json**: 基准测试结果 + StorageMonitor 实时指标
2. **trace.csv.zst**: 压缩的操作级 IO 追踪（IOTracer）
3. **stdout**: DEBUG 级别的详细日志

### 后处理分析
```bash
# 解压追踪文件
zstdcat trace.csv.zst > trace.csv

# 分析追踪数据
python3 -c "
import pandas as pd
df = pd.read_csv('trace.csv')

# 按操作类型统计
print(df.groupby('Operation')['Object_Size_Bytes'].agg(['count', 'sum', 'mean']))

# 按层级统计
print(df.groupby('Tier')['Object_Size_Bytes'].sum() / (1024**3), 'GiB')

# 时间分布
df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')
df.set_index('Timestamp').resample('1S')['Object_Size_Bytes'].sum().plot()
"
```

---

## 7. 功能对比表

| 功能 | IOTracer | StorageMonitor | 设备延迟追踪 | 后端延迟追踪 |
|------|----------|----------------|--------------|--------------|
| **粒度** | 操作级 | 秒级聚合 | 块设备级 | 后端函数级 |
| **性能影响** | 1-2% | <0.5% | 1-3% | <0.1% |
| **存储开销** | 中（压缩后小） | 低 | 低 | 无（内存） |
| **需要权限** | 否 | 否 | 是（sudo） | 否 |
| **输出格式** | CSV | JSON | 直方图 | 对象属性 |
| **适用场景** | 详细分析 | 实时监控 | 内核调试 | 代码优化 |

---

## 8. 最佳实践

### 开发调试
```bash
# 启用所有 profiling 功能
--io-trace-log trace.csv.zst \
--enable-latency-tracing \
--log-level DEBUG
```

### 性能基准测试
```bash
# 最小化 profiling 开销
--log-level INFO
# 不启用 --io-trace-log
# 不启用 --enable-latency-tracing
# StorageMonitor 自动启用（开销极低）
```

### 生产环境问题排查
```bash
# 平衡详细程度和性能
--io-trace-log trace.csv.zst \
--log-level WARNING
# 不启用 --enable-latency-tracing
```

---

## 9. 相关文件

- `kv_cache/tracer.py`: IOTracer 实现
- `kv_cache/monitoring.py`: StorageMonitor 实现
- `kv_cache/backends.py`: IOTiming 数据类
- `kv_cache/cli.py`: CLI 参数定义
- `kv_cache/cache.py`: Cache 类集成 IOTracer 和 StorageMonitor

---

## 总结

KV Cache 基准测试已具备完整的 IO profiling 能力，涵盖：

1. **操作级追踪**（IOTracer）- 记录每个IO操作的详细信息
2. **实时监控**（StorageMonitor）- 秒级聚合性能指标
3. **设备级分析**（bpftrace）- 内核块设备层延迟追踪
4. **延迟分解**（IOTiming）- 区分设备延迟和主机处理延迟
5. **灵活日志**（log-level）- 可调节的详细程度

这些功能已完整实现并集成到基准测试框架中，**无需额外开发新工具**。
