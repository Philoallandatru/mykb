# NVIDIA Dynamo KV Cache Offloading 用户指南

**来源**: https://docs.nvidia.com/dynamo/v-0-9-0/user-guides/kv-cache-offloading  
**版本**: v0.9.0  
**组件**: KVBM (KV Block Manager)

---

## 概述

### KVBM 是什么

KVBM（KV Block Manager）是一个**可扩展的运行时组件**，设计用于处理推理任务中 Key-Value 块的内存分配、管理和远程共享。

**定位**: 作为 vLLM 和 TensorRT-LLM 等框架的统一内存层，支持异构和分布式环境。

### 核心特性

1. **模块化设计** - 可独立使用（`pip install kvbm`）或作为完整 Dynamo 栈的一部分
2. **分层缓存架构** - GPU → CPU → Disk
3. **分离式服务支持** - prefill 和 decode 分离运行
4. **度量指标** - 提供性能监控指标

---

## 支持的存储层级

### 选项 1: 仅 CPU 缓存（GPU → CPU 卸载）

```bash
export DYN_KVBM_CPU_CACHE_GB=4  # 4GB 固定 CPU 内存
```

**用途**: 将 KV cache 从 GPU 卸载到 CPU RAM

---

### 选项 2: CPU + 磁盘缓存（GPU → CPU → 磁盘分层卸载）

```bash
export DYN_KVBM_CPU_CACHE_GB=4
export DYN_KVBM_DISK_CACHE_GB=8  # 8GB 磁盘
```

**用途**: 三层缓存，磁盘作为最后一层

---

### 选项 3: 仅磁盘缓存（GPU → 磁盘直接卸载）⚠️ 实验性

```bash
export DYN_KVBM_DISK_CACHE_GB=8
```

**注意**: 直接 GPU → Disk 卸载为实验性功能，可能性能不佳

---

## 支持的框架后端

| 框架 | 集成方式 | 版本要求 |
|------|---------|---------|
| **vLLM** | 通过 `DynamoConnector` | - |
| **TensorRT-LLM** | PyTorch 后端 | v1.2.0rc2 或更新 |
| **SGLang HiCache** | NIXL 存储后端 | - |

---

## 配置方法

### 核心环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DYN_KVBM_CPU_CACHE_GB` | CPU 缓存大小（GB） | - |
| `DYN_KVBM_DISK_CACHE_GB` | 磁盘缓存大小（GB） | - |
| `DYN_KVBM_CPU_CACHE_OVERRIDE_NUM_BLOCKS` | 精确指定 CPU 块数量 | - |
| `DYN_KVBM_DISK_CACHE_OVERRIDE_NUM_BLOCKS` | 精确指定磁盘块数量 | - |
| `DYN_KVBM_METRICS` | 启用度量指标 | false |
| `DYN_KVBM_DISABLE_DISK_OFFLOAD_FILTER` | 禁用磁盘卸载过滤 | false |
| `DYN_KVBM_LEADER_WORKER_INIT_TIMEOUT_SECS` | 初始化超时时间（秒） | 1800 |
| `DYN_KVBM_DISK_ZEROFILL_FALLBACK` | 启用磁盘零填充回退 | false |
| `DYN_KVBM_DISK_DISABLE_O_DIRECT` | 禁用 O_DIRECT 标志 | false |

---

## KVBM 工作原理

### 架构组件

```
┌─────────────────────────────────────────────────────────┐
│               KVBM Architecture                         │
│                                                         │
│  ┌──────────────┐                                      │
│  │ Leader/Worker│  ← etcd 注册和发现                    │
│  │   模式        │                                      │
│  └──────┬───────┘                                      │
│         │                                              │
│  ┌──────▼─────────────────────────────────────┐       │
│  │     分层缓存策略                              │       │
│  │  GPU → CPU → Disk 多级缓存                   │       │
│  └──────┬─────────────────────────────────────┘       │
│         │                                              │
│  ┌──────▼───────┐  ┌──────────────┐                   │
│  │  块管理       │  │  远程共享     │                   │
│  │  分配和回收   │  │  跨节点共享   │                   │
│  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### 磁盘卸载过滤机制

**目的**: 延长 SSD 寿命

**策略**:
- 仅当 KV 块频率 ≥ 2 时才卸载到磁盘
- 缓存命中时频率翻倍（初始值为 1）
- 每次时间衰减步骤频率减 1

**禁用**:
```bash
export DYN_KVBM_DISABLE_DISK_OFFLOAD_FILTER=true
```

---

## vLLM 集成

### 方式 1: 使用 vllm serve

```bash
vllm serve \
  --kv-transfer-config '{
    "kv_connector":"DynamoConnector",
    "kv_role":"kv_both",
    "kv_connector_module_path": "kvbm.vllm_integration.connector"
  }' \
  Qwen/Qwen3-0.6B
```

### 方式 2: 使用 dynamo.vllm

```bash
DYN_KVBM_CPU_CACHE_GB=20 \
python -m dynamo.vllm \
    --model Qwen/Qwen3-0.6B \
    --enforce-eager \
    --connector kvbm
```

### 聚合式服务（Aggregated Serving）

```bash
cd $DYNAMO_HOME/examples/backends/vllm
./launch/agg_kvbm.sh
```

### 分离式服务（Disaggregated Serving - 1P1D）

```bash
# 需要至少 2 个 GPU
./launch/disagg_kvbm.sh
```

**1P1D 架构**:
```
Prefill Worker (GPU 0)
  ↓ KV cache transfer
Decode Worker (GPU 1)
```

---

## TensorRT-LLM 集成

### 配置文件

```yaml
backend: pytorch
cuda_graph_config: null
kv_cache_config:
  enable_partial_reuse: false  # 必须禁用，以增加卸载缓存命中
  free_gpu_memory_fraction: 0.80
kv_connector_config:
  connector_module: kvbm.trtllm_integration.connector
  connector_scheduler_class: DynamoKVBMConnectorLeader
  connector_worker_class: DynamoKVBMConnectorWorker
```

### 启动步骤

```bash
# 1. 创建配置文件
cat > "/tmp/kvbm_llm_api_config.yaml" <<EOF
backend: pytorch
kv_cache_config:
  enable_partial_reuse: false
  free_gpu_memory_fraction: 0.80
kv_connector_config:
  connector_module: kvbm.trtllm_integration.connector
  connector_scheduler_class: DynamoKVBMConnectorLeader
  connector_worker_class: DynamoKVBMConnectorWorker
EOF

# 2. 启动前端
python3 -m dynamo.frontend --http-port 8000 &

# 3. 启动模型服务
DYN_KVBM_CPU_CACHE_GB=20 \
python3 -m dynamo.trtllm \
  --model-path Qwen/Qwen3-0.6B \
  --served-model-name Qwen/Qwen3-0.6B \
  --extra-engine-args /tmp/kvbm_llm_api_config.yaml &
```

---

## 性能监控

### 启用监控栈

```bash
# 启动 Prometheus 和 Grafana
docker compose -f deploy/docker-observability.yml up -d

# 访问 Grafana: http://localhost:3000
# 默认登录: dynamo/dynamo
```

### 启用 KVBM 度量指标

```bash
DYN_KVBM_METRICS=true \
DYN_KVBM_CPU_CACHE_GB=20 \
python -m dynamo.vllm \
    --model Qwen/Qwen3-0.6B \
    --enforce-eager \
    --connector kvbm
```

### 关键指标

| 指标名 | 含义 |
|--------|------|
| `kvbm_matched_tokens` | 匹配的 token 数量（缓存命中） |
| `kvbm_offload_blocks_d2h` | Device 到 Host 卸载块数 |
| `kvbm_offload_blocks_h2d` | Host 到 Disk 卸载块数 |
| `kvbm_onboard_blocks_h2d` | Host 到 Device 加载块数 |
| `kvbm_host_cache_hit_rate` | Host 缓存命中率（0.0-1.0） |
| `kvbm_disk_cache_hit_rate` | Disk 缓存命中率（0.0-1.0） |

---

## 性能基准测试

### 使用 LMBenchmark

```bash
git clone https://github.com/LMCache/LMBenchmark.git
cd LMBenchmark/synthetic-multi-round-qa

./long_input_short_output_run.sh \
    "Qwen/Qwen3-0.6B" \
    "http://localhost:8000" \
    "benchmark_kvbm" \
    1
```

---

## 故障排查

### 问题 1: 无 TTFT 性能提升

**症状**: 启用 KVBM 后，TTFT 没有明显改善

**原因**: 前缀缓存命中不足

**解决**:
1. 检查 Grafana 中的 `Onboard Blocks` 指标
2. 确认是否有大量 KV 块被加载
3. 验证请求是否有共同的前缀

---

### 问题 2: Worker 初始化超时

**症状**: Worker 启动时超时失败

**解决**:
```bash
export DYN_KVBM_LEADER_WORKER_INIT_TIMEOUT_SECS=3600
```

---

### 问题 3: 磁盘卸载启动失败

**症状**: 在 Lustre 等网络文件系统上启动失败

**原因**: 文件系统不支持 `fallocate()`

**解决**:
```bash
export DYN_KVBM_DISK_ZEROFILL_FALLBACK=true
export DYN_KVBM_DISK_DISABLE_O_DIRECT=true  # 如遇 EINVAL 错误
```

---

### 问题 4: TensorRT-LLM 分离式服务挂起

**症状**: 使用 TensorRT-LLM 1.3.0rc1 的分离式服务时请求挂起

**解决**: 使用特定 commit 版本
```bash
git checkout 18e611da773026a55d187870ebcfa95ff00c8482
```

---

## 完整部署示例

### vLLM 聚合式服务

```bash
# 1. 启动 etcd
docker compose -f deploy/docker-compose.yml up -d

# 2. 构建容器
./container/build.sh --framework vllm

# 3. 运行容器
./container/run.sh --framework vllm -it --mount-workspace --use-nixl-gds

# 4. 启动服务
cd $DYNAMO_HOME/examples/backends/vllm
./launch/agg_kvbm.sh

# 5. 测试请求
curl localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "stream": false,
    "max_tokens": 10
  }'
```

---

## 限制和注意事项

### 版本要求

| 组件 | 版本要求 | 注意事项 |
|------|---------|---------|
| **TensorRT-LLM** | v1.2.0rc2+ | 仅支持 PyTorch 后端 |
| **TensorRT-LLM 分离式** | commit `18e611da` | 1.3.0rc1 有挂起问题 |
| **vLLM** | - | 无特殊限制 |

### 配置限制

#### TensorRT-LLM 限制
1. 仅支持 PyTorch 后端
2. 必须禁用部分重用（`enable_partial_reuse: false`）
3. 分离式服务需要特定 commit 版本

#### 磁盘缓存限制
1. 直接 GPU → Disk 卸载为**实验性功能**，可能性能不佳
2. 磁盘卸载过滤在直接卸载模式下不支持
3. Lustre 等网络文件系统可能需要特殊配置

#### 硬件要求
1. 分离式服务最少需要 **2 个 GPU**（1P1D）
2. 2P2D 配置需要至少 **4 个 GPU**

#### 文件系统兼容性
1. 某些网络文件系统不支持 `fallocate()`
2. 可能需要启用 zerofill fallback 或禁用 O_DIRECT

---

## 最佳实践

### 配置建议

#### 1. 内存分配
```bash
# 小型模型（7B-13B）
export DYN_KVBM_CPU_CACHE_GB=4
export DYN_KVBM_DISK_CACHE_GB=8

# 大型模型（70B+）
export DYN_KVBM_CPU_CACHE_GB=20
export DYN_KVBM_DISK_CACHE_GB=40
```

#### 2. TensorRT-LLM 特定设置
```yaml
kv_cache_config:
  enable_partial_reuse: false  # 必须禁用
  free_gpu_memory_fraction: 0.80
```

#### 3. 分离式服务
- Prefill worker 启用 KVBM 进行 KV 缓存卸载
- Decode worker 专注于生成任务

#### 4. 性能监控
- 启动前确保 etcd 和 nats 服务正在运行
- 使用度量指标验证缓存命中率
- 根据实际工作负载调整缓存大小
- 对于 SSD，保持默认的磁盘卸载过滤策略

---

## 与其他系统对比

| 系统 | 定位 | 存储层级 | 分离式服务 |
|------|------|---------|-----------|
| **NVIDIA Dynamo KVBM** | 企业级统一内存层 | GPU→CPU→Disk | ✅ 原生支持 |
| **llm-d filesystem** | K8s原生共享存储 | GPU→Shared FS | ✅ 跨replica |
| **LMCache** | 轻量级offload | GPU→CPU→Disk | ❌ 单节点 |

**KVBM 优势**:
1. 统一的内存管理层（支持 vLLM 和 TensorRT-LLM）
2. 原生分离式服务支持
3. 企业级监控和度量指标
4. Leader/Worker 模式的分布式架构

---

## 架构图

### 三层缓存架构

```
┌─────────────────────────────────────────────────────┐
│                vLLM / TensorRT-LLM                  │
│                 (Inference Engine)                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│                  KVBM Layer                         │
│            (统一内存管理层)                           │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ GPU HBM  │→ │ CPU RAM  │→ │  Disk/SSD    │     │
│  │ (L1)     │  │ (L2)     │  │  (L3)        │     │
│  │ 80GB     │  │ 4-20GB   │  │  8-40GB      │     │
│  └──────────┘  └──────────┘  └──────────────┘     │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Leader/Worker via etcd                     │   │
│  │  - 块管理                                    │   │
│  │  - 远程共享                                  │   │
│  │  - 度量指标                                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 相关概念

- [[dynamo]] - NVIDIA Dynamo分布式推理平台
- [[kv-cache]] - KV cache核心概念
- [[vllm]] - vLLM推理框架
- [[tensorrt-llm]] - TensorRT-LLM推理引擎
- [[ai-ssd]] - AI SSD核心定义
- [[inference-frameworks-offload-mechanisms]] - 推理框架offload机制

---

**标签**: #dynamo #kvbm #kv-cache #offload #nvidia #vllm #tensorrt-llm #distributed
