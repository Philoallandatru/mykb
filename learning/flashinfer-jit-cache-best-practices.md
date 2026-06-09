---
tags:
- llm-inference
- performance-tuning
- best-practices
created: '2026-06-08'
---

# flashinfer-jit-cache-best-practices

## JIT 缓存机制深入理解

### 为什么需要 JIT 缓存？

**问题**: LLM 推理中 attention 计算的参数空间巨大
- 不同的序列长度（128, 256, 512, 1024, ...）
- 不同的批次大小（1, 2, 4, 8, ...）
- 不同的头数（32, 40, 64, ...）
- 不同的数据类型（fp16, bf16, fp8, ...）

**解决方案**: JIT 编译 + 缓存
- 静态编译所有组合 → 不现实（组合爆炸）
- 每次运行时编译 → 太慢（1-5秒延迟）
- JIT + 缓存 → 最佳平衡

### 缓存实现细节

#### 缓存键生成
```python
cache_key = hash(
    kernel_name,
    seq_len,
    batch_size, 
    num_heads,
    head_dim,
    dtype,
    cuda_arch
)
```

#### 缓存文件结构
```
~/.cache/flashinfer/
├── cuda_11.8/
│   ├── sm_80/  # A100
│   │   ├── kernel_xyz_hash1.cubin
│   │   └── kernel_xyz_hash2.cubin
│   └── sm_89/  # L40S/H100
│       └── kernel_xyz_hash3.cubin
└── cuda_12.1/
    └── ...
```

## 性能优化策略

### 1. 预热缓存

**生产环境必做**: 在服务启动前遍历常用参数组合

```python
# warmup.py
for seq_len in [128, 256, 512, 1024, 2048]:
    for batch_size in [1, 2, 4, 8]:
        # 触发编译
        run_inference(seq_len, batch_size)
```

**Why**: 避免首个用户请求承受编译延迟  
**How to apply**: 将预热脚本集成到容器启动脚本

### 2. 持久化存储

**容器场景**: 将缓存目录挂载到宿主机

```yaml
# docker-compose.yml
volumes:
  - /host/flashinfer-cache:/root/.cache/flashinfer
```

**Why**: 容器重启后缓存不丢失  
**How to apply**: K8s 使用 PVC，Docker 使用 named volume

### 3. 缓存大小管理

**建议配置**:
- 开发环境: 500MB (够用)
- 生产环境: 2GB (覆盖常用组合)
- 多模型共享: 5GB+

**Why**: 避免磁盘占满 + 控制缓存命中率  
**How to apply**: 设置 `FLASHINFER_CACHE_SIZE_MB` 环境变量

### 4. 监控缓存效率

**关键指标**:
- 缓存命中率 (目标 > 95%)
- 编译时间分布
- 缓存文件数量和总大小

```python
# 日志分析
grep "JIT compile" service.log | wc -l  # 编译次数
grep "Cache hit" service.log | wc -l    # 命中次数
```

**Why**: 低命中率说明参数空间覆盖不足  
**How to apply**: 定期分析日志，调整预热策略

## 故障排查

### 问题 1: 每次启动都重新编译

**原因**: 缓存目录权限问题或容器未持久化  
**解决**: 检查目录权限，挂载 volume

### 问题 2: 磁盘占用过大

**原因**: 缓存未设置大小限制  
**解决**: 设置 `FLASHINFER_CACHE_SIZE_MB`，定期清理

### 问题 3: CUDA 版本升级后缓存失效

**原因**: 缓存键包含 CUDA 版本  
**解决**: 正常现象，重新预热即可

## 与其他缓存机制对比

| 缓存类型 | 存储位置 | 作用域 | 典型场景 |
|---------|---------|--------|----------|
| FlashInfer JIT | 文件系统 | 全局 | Attention 内核 |
| Triton Cache | 文件系统 | 全局 | torch.compile |
| CUDA JitCache | 进程内存 | 单进程 | PyTorch JIT |
| KV Cache | GPU 显存 | 单次推理 | LLM 上下文 |

## 未来优化方向

1. **网络共享缓存**: 多机共享编译结果
2. **智能预热**: 根据历史请求预测参数分布
3. **分层缓存**: 热点内核放内存，冷门放磁盘


## 核心洞察

1. JIT 缓存是动态编译和静态编译之间的最佳平衡点
2. 生产环境必须预热缓存，避免首个用户请求的编译延迟
3. 容器化部署时，缓存目录必须持久化到宿主机或 PVC
4. 缓存命中率是关键性能指标，目标应 > 95%
5. CUDA 版本、GPU 架构都会影响缓存键，升级时需重新预热
6. 合理设置缓存大小限制，避免磁盘占满
7. JIT 缓存机制可复用到其他 CUDA kernel 优化场景


## 相关概念

- [[flashinfer-jit-cache]]
- [[flashinfer]]
- [[vllm]]
