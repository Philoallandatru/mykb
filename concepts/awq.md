---
aliases:
- activation-aware-quantization
tags:
- quantization
- model-compression
- int4
- optimization
created: '2026-06-10'
---

# awq

## 定义

AWQ (Activation-aware Weight Quantization) 是一种先进的权重量化方法，通过分析激活分布来保护重要权重通道，实现 INT4 量化而几乎不损失模型性能。

## 核心创新

### 传统量化的问题
- **均等对待**: 所有权重通道使用相同量化策略
- **性能损失**: INT4 量化导致显著精度下降
- **忽略激活**: 只看权重统计，忽略实际激活影响

### AWQ 解决方案
**核心思想**: 保护对激活影响大的权重通道

```
观察: 少数权重通道对输出影响巨大
策略: 根据激活幅度调整量化精度
结果: INT4 量化，接近 FP16 性能
```

## 技术原理

### 激活感知
**分析激活统计**:
```python
# 计算每个通道的重要性
importance = torch.mean(torch.abs(activations), dim=0)

# 根据重要性调整量化 scale
scale = scale * (importance ** alpha)
```

**alpha 参数**:
- 控制保护程度
- 通常 α = 0.5 效果最好
- 平衡精度和压缩率

### 逐通道量化
```
标准量化 (per-tensor):
  整个矩阵用一个 scale
  
AWQ (per-channel):
  每个输出通道独立 scale
  重要通道: 更细的量化粒度
  次要通道: 更粗的量化粒度
```

### 量化公式
```
原始权重: W (FP16)
激活重要性: s = (|X|.mean(0)) ** alpha
调整后权重: W' = W × diag(s)
量化: Q = round(W' / scale) → INT4
反量化: W_quant = Q × scale / s
```

## 性能表现

### 压缩率
- **INT4**: 4 bits per parameter
- **压缩比**: 4× vs FP16
- **内存节省**: 75%

### 精度保持

| 模型 | FP16 | INT4 (AWQ) | 精度损失 |
|------|------|------------|----------|
| LLaMA-7B | 73.5% | 73.0% | -0.5% |
| LLaMA-13B | 76.9% | 76.4% | -0.5% |
| LLaMA-30B | 79.2% | 78.9% | -0.3% |

**对比其他量化**:
- GPTQ (INT4): -1.0 ~ -1.5%
- Round-to-Nearest (INT4): -3 ~ -5%

### 推理速度
- **内存带宽**: 降低 75%
- **吞吐量**: 提升 2-3×
- **延迟**: 降低 40-60%

## 实现细节

### 校准过程
```python
# 1. 收集激活统计
model.eval()
for batch in calibration_data:
    with torch.no_grad():
        activations = model(batch)
        collect_statistics(activations)

# 2. 计算最优 scale
for layer in model.layers:
    importance = compute_importance(layer)
    layer.scale = compute_scale(layer.weights, importance)

# 3. 量化权重
    layer.weights_int4 = quantize(layer.weights, layer.scale)
```

### 推理优化
```python
# 使用 INT4 GEMM
output = int4_gemm(
    input_fp16,
    weights_int4,
    scale,
    importance_factors
)
```

## 使用方法

### AutoAWQ 库
```python
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

# 加载模型和量化
model = AutoAWQForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf"
)

# 量化配置
quant_config = {
    "zero_point": True,
    "q_group_size": 128,
    "w_bit": 4,
    "version": "GEMM"
}

# 执行量化
model.quantize(
    tokenizer,
    quant_config=quant_config,
    calib_data=calibration_data
)

# 保存量化模型
model.save_quantized("llama-7b-awq")
```

### vLLM 集成
```python
from vllm import LLM

# 直接加载 AWQ 量化模型
llm = LLM(
    model="llama-7b-awq",
    quantization="awq",
    dtype="float16"
)

# 推理
outputs = llm.generate(prompts)
```

## 硬件支持

### GPU 要求
- **NVIDIA**: Ampere+ (RTX 30/40, A100, H100)
- **INT4 Tensor Core**: 原生支持
- **CUDA**: 11.8+

### 性能提升

| GPU | FP16 | AWQ INT4 | 加速比 |
|-----|------|----------|--------|
| RTX 4090 | 45 tok/s | 120 tok/s | 2.7× |
| A100 | 60 tok/s | 150 tok/s | 2.5× |
| H100 | 120 tok/s | 280 tok/s | 2.3× |

## 与其他量化对比

### vs GPTQ
- **AWQ**: 激活感知，精度更高
- **GPTQ**: 二阶信息，速度较慢
- **结果**: AWQ 通常精度高 0.5-1%

### vs GGUF
- **AWQ**: GPU 优化，推理更快
- **GGUF**: CPU 友好，部署灵活
- **场景**: AWQ 服务器，GGUF 边缘设备

### vs SmoothQuant
- **AWQ**: 仅权重量化（W4A16）
- **SmoothQuant**: 权重+激活量化（W8A8）
- **压缩比**: AWQ 4×, SmoothQuant 2×

## 适用场景

### 推荐使用
✓ **内存受限**: GPU 显存不足
✓ **高吞吐**: 需要服务大量并发
✓ **成本敏感**: 减少 GPU 数量
✓ **长上下文**: 节省 KV cache 空间

### 不太适合
✗ **极致精度**: 科研任务要求无损
✗ **小模型**: < 7B 量化收益有限
✗ **CPU 推理**: AWQ 优化 GPU

## 最佳实践

### 1. 校准数据
- **数量**: 128-512 样本
- **分布**: 覆盖目标任务
- **质量**: 代表性强

### 2. Group Size
```python
# 较小 group (64-128): 精度高，推理略慢
# 较大 group (256): 精度略低，推理更快
# 推荐: 128 (平衡)
```

### 3. 监控指标
- **Perplexity**: 语言建模能力
- **Accuracy**: 下游任务表现
- **Throughput**: 实际吞吐量

### 4. A/B 测试
- 量化前后对比
- 真实负载测试
- 用户体验验证

## 研究和发展

### 论文
- **AWQ: Activation-aware Weight Quantization** (2023)
- MIT Han Lab

### 代码
- **AutoAWQ**: https://github.com/casper-hansen/AutoAWQ
- **vLLM AWQ**: 官方集成

### 未来方向
1. **更低精度**: INT3, INT2
2. **动态量化**: 运行时调整
3. **混合精度**: 层级别选择精度

## 相关概念

- [[gptq]]
- [[gguf]]
- [[kv-cache-quantization]]
- [[model-compression]]
