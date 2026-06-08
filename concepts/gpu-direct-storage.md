---
aliases:
- gds
- direct-storage
tags:
- storage
- io-optimization
- nvidia
- performance
created: '2026-06-09'
---

# gpu-direct-storage

## 定义

GPU Direct Storage (GDS) 是 NVIDIA 的技术，允许 GPU 直接从存储设备（NVMe SSD）读写数据，绕过 CPU 和系统内存，显著降低延迟并提升吞吐量。

## 传统 I/O 路径问题

### 标准数据路径
```
SSD → CPU Memory → CPU 处理 → GPU Memory → GPU 计算
     PCIe          系统总线      PCIe
```

**问题**:
1. **多次拷贝**: SSD → CPU → GPU (2次)
2. **CPU 开销**: CPU 参与数据搬运
3. **延迟累积**: 多个传输阶段
4. **带宽浪费**: 数据经过系统总线
5. **内存占用**: CPU 内存作为中转

### 性能影响
- **延迟**: 额外 100-500μs
- **CPU 利用率**: 10-30% CPU 用于数据搬运
- **吞吐量**: 受限于 CPU 内存带宽

## GPU Direct Storage 架构

### 直接路径
```
NVMe SSD ─────→ GPU Memory ─────→ GPU 计算
         PCIe 直接传输
```

**优势**:
1. **零拷贝**: 数据直接到 GPU
2. **CPU 解放**: CPU 不参与数据传输
3. **低延迟**: 减少 50-70% 延迟
4. **高吞吐**: 充分利用 PCIe 带宽
5. **内存节省**: 不占用 CPU 内存

### 技术组件

#### 1. cuFile API
```c
// 直接读取到 GPU 内存
CUfileHandle_t fh;
cuFileHandleRegister(&fh, fd);

// 数据直接从 SSD 到 GPU
cuFileRead(fh, gpu_buffer, size, offset, 0);
```

#### 2. 存储驱动
- **NVIDIA GPUDirect Storage Driver**
- **NVMe 驱动支持**
- **文件系统集成**

#### 3. DMA 引擎
- PCIe peer-to-peer 传输
- RDMA (Remote DMA)
- 无需 CPU 参与

## 性能提升

### 延迟降低

**传统路径**:
```
SSD → CPU: 50-100μs
CPU → GPU: 50-100μs
总计: 100-200μs
```

**GDS 路径**:
```
SSD → GPU: 30-80μs
降低: 50-70%
```

### 吞吐量提升

**单个 NVMe SSD**:
- 传统: 3-4 GB/s (CPU 瓶颈)
- GDS: 6-7 GB/s (接近 SSD 峰值)
- 提升: 1.5-2×

**多个 NVMe SSD**:
- 传统: 6-8 GB/s (系统总线瓶颈)
- GDS: 20-30 GB/s (聚合带宽)
- 提升: 3-4×

### CPU 利用率
- 传统: 10-30% CPU 用于 I/O
- GDS: < 1% CPU
- 释放: 10-30% CPU 可用于其他任务

## LLM 推理应用场景

### 1. 模型加载

**场景**: 从 SSD 加载大模型

**传统方式**:
```python
# 需要经过 CPU 内存
model = torch.load("model.bin")  # SSD → CPU
model.to("cuda")                 # CPU → GPU
```

**GDS 方式**:
```c
// 直接加载到 GPU
cuFileRead(fh, gpu_buffer, model_size, 0, 0);
```

**提升**:
- LLaMA-70B (140GB): 加载时间 35s → 20s
- 降低 40% 加载延迟

### 2. KV Cache Offload

**场景**: KV cache 在 SSD 和 GPU 之间交换

**数据流**:
```
请求到达:
  SSD (历史 KV) ─GDS→ GPU ─→ 计算
  
请求完成:
  GPU (新 KV) ─GDS→ SSD (持久化)
```

**提升**:
- 读取 1GB KV: 250ms → 150ms
- 写入 1GB KV: 300ms → 180ms

### 3. 多模态数据加载

**场景**: 加载大规模图像/视频数据

**应用**:
- CLIP 推理: 图像直接到 GPU
- 视频处理: 帧数据流式传输
- RAG 系统: 文档快速加载

**提升**:
- 图像批次加载: 2-3× 吞吐量
- 视频处理: 延迟降低 50%

### 4. Checkpoint 保存

**场景**: 训练 checkpoint 快速保存

**传统**:
```
GPU → CPU Memory → SSD
     100ms           200ms
总计: 300ms
```

**GDS**:
```
GPU ───→ SSD
     150ms
```

**提升**:
- 大模型 checkpoint: 节省 30-50% 时间

## 硬件要求

### GPU 要求
- **架构**: NVIDIA Ampere+ (A100, H100, RTX 30/40 系列)
- **驱动**: CUDA 11.4+
- **特性**: PCIe BAR1 支持

### 存储要求
- **类型**: NVMe SSD (PCIe 3.0/4.0/5.0)
- **控制器**: 支持 GPUDirect Storage
- **文件系统**: ext4, XFS (推荐 XFS)

### 系统要求
- **OS**: Linux (Ubuntu 20.04+, RHEL 8+)
- **PCIe**: 足够的 PCIe lanes
- **驱动**: NVIDIA GDS 驱动

## 配置和使用

### 安装 GDS
```bash
# 安装 NVIDIA GDS 驱动
sudo apt install nvidia-gds

# 验证安装
gdscheck -p
```

### cuFile 配置
```json
// /etc/cufile.json
{
    "logging": {
        "dir": "/var/log/cufile",
        "level": "INFO"
    },
    "profile": {
        "nvtx": false,
        "cufile_stats": 0
    },
    "execution": {
        "max_io_threads": 8,
        "max_io_queue_depth": 128,
        "parallel_io": true,
        "min_io_threshold": 4096
    }
}
```

### Python 集成 (Rapids cuFile)
```python
from cufile import CuFile

# 打开文件
cf = CuFile("large_model.bin", "r")

# 直接读取到 GPU
gpu_buffer = cf.read(device_buffer)

# 关闭
cf.close()
```

## 性能调优

### 1. I/O 对齐
```c
// 数据对齐到 4KB 边界
offset = (offset + 4095) & ~4095;
size = (size + 4095) & ~4095;
```

### 2. 异步 I/O
```c
// 启动异步读取
cuFileReadAsync(fh, gpu_buffer, size, offset, 0, 0);

// 继续其他工作
do_computation();

// 等待完成
cuFileWaitAsync();
```

### 3. 批量操作
```c
// 批量读取多个文件
CUfileIOParams_t io_batch[N];
cuFileBatchIOSetUp(io_batch, N);
cuFileBatchIOSubmit(io_batch, N, ...);
```

### 4. Pinned Memory
```c
// 使用 pinned memory 提升传输速度
cudaMallocHost(&pinned_buffer, size);
```

## 监控和诊断

### 性能指标
```bash
# 查看 GDS 统计
nvidia-smi nvlink --status
nvidia-smi gds --status

# cuFile 性能分析
cufile_stats
```

### 关键指标
- **吞吐量**: GB/s
- **IOPS**: 操作/秒
- **延迟**: μs
- **CPU 利用率**: %

### 调试工具
```bash
# GDS 健康检查
gdscheck -p

# 测试性能
gdsio -f /path/to/file -s 1G -w 4
```

## 限制和注意事项

### 1. 硬件限制
- 需要 Ampere+ GPU
- 需要 NVMe SSD
- PCIe lanes 充足

### 2. 软件限制
- Linux only (暂无 Windows)
- 特定文件系统 (ext4, XFS)
- CUDA 版本要求

### 3. 使用场景
- 适合大文件 I/O (> 4MB)
- 小文件可能没有收益
- 随机 I/O 效果较差

### 4. 成本
- 需要企业级 NVMe SSD
- 需要特定 GPU 型号
- 开发复杂度增加

## 与其他技术对比

### vs 标准 I/O
- **延迟**: GDS 降低 50-70%
- **吞吐**: GDS 提升 1.5-3×
- **CPU**: GDS 节省 10-30%

### vs RDMA (网络)
- **场景**: GDS 本地存储，RDMA 远程
- **延迟**: 相似（μs 级别）
- **带宽**: GDS 更高（本地 PCIe）

### vs NVMe-oF
- **GDS**: 直接访问本地 SSD
- **NVMe-oF**: 通过网络访问远程 SSD
- **延迟**: GDS 更低

## 未来发展

### CXL Storage
- **统一内存**: CPU/GPU/Storage 统一寻址
- **缓存一致性**: 硬件支持
- **更低延迟**: < GDS

### PCIe 6.0/7.0
- **带宽翻倍**: 每代翻倍
- **GDS 受益**: 更高吞吐量

### 软件生态
- **框架集成**: PyTorch, TensorFlow
- **应用优化**: 自动使用 GDS
- **云平台**: 云服务商支持


## 相关概念

- [[cpu-offload]]
- [[nvme-ssd]]
- [[pcie-bandwidth]]
