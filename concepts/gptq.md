---
aliases:
- generalized-post-training-quantization
tags:
- quantization
- model-compression
- post-training
- int4
created: '2026-06-10'
---

# gptq

## 定义

GPTQ (Generalized Post-Training Quantization) 是一种基于二阶信息的训练后量化方法，能够将大型语言模型压缩到 3-4 bits，同时保持接近原始精度。

## 核心技术

### 最优脑量化 (OBQ)
**理论基础**: 利用 Hessian 矩阵的二阶信息

```
目标: 最小化量化误差
方法: 考虑权重间的相互影响
结果: 更优的量化精度
```

### 逐层量化
```
顺序处理:
  Layer 1 → 量化 → 记录误差
  Layer 2 → 量化 → 补偿上层误差
  ...
  Layer N → 量化 → 最终调整
```

## 算法原理

### Hessian 矩阵
```
权重更新的敏感度:
H = ∂²L / ∂W²

高 Hessian 值 → 权重重要 → 精细量化
低 Hessian 值 → 权重次要 → 粗糙量化
```

### 误差补偿
```python
# 伪代码
for weight in layer_weights:
    # 量化当前权重
    quant_error = quantize(weight) - weight
    
    # 补偿到未量化的权重
    remaining_weights += compensate(quant_error, H_inv)
```

### 分组量化
```
Group Size = 128:
  每128个权重共享一个 scale
  平衡精度和开销
  
Group Size = -1:
  整个矩阵一个 scale
  最大压缩，精度略降
```

## 性能表现

### 压缩效果

| 模型 | FP16 | GPTQ 4bit | GPTQ 3bit |
|------|------|-----------|-----------|
| LLaMA-7B | 13.5GB | 3.9GB | 2.9GB |
| LLaMA-13B | 25GB | 7.3GB | 5.5GB |
| LLaMA-65B | 123GB | 36GB | 27GB |

### 精度保持

**LLaMA 模型 (WikiText2 PPL)**:
- FP16: 5.68
- GPTQ 4bit: 5.83 (+0.15)
- GPTQ 3bit: 6.05 (+0.37)

**下游任务 (平均准确率)**:
- FP16: 100%
- GPTQ 4bit: 99.2%
- GPTQ 3bit: 97.8%

### 量化时间
```
LLaMA-7B:
- 校准: ~10分钟 (GPU)
- 量化: ~5分钟
- 总计: ~15分钟

LLaMA-65B:
- 校准: ~45分钟
- 量化: ~20分钟
- 总计: ~65分钟
```

## 实现和使用

### AutoGPTQ 库
```python
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
from transformers import AutoTokenizer

# 量化配置
quantize_config = BaseQuantizeConfig(
    bits=4,                    # 4-bit 量化
    group_size=128,           # 分组大小
    desc_act=False,           # 激活顺序
    damp_percent=0.01,        # 阻尼系数
)

# 加载模型
model = AutoGPTQForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-hf",
    quantize_config
)

# 执行量化
model.quantize(calibration_data)

# 保存
model.save_quantized("llama-7b-gptq")
```

### vLLM 加载
```python
from vllm import LLM

llm = LLM(
    model="llama-7b-gptq",
    quantization="gptq",
    dtype="float16"
)
```

### HuggingFace 集成
```python
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Llama-2-7B-GPTQ",
    device_map="auto",
    trust_remote_code=True
)
```

## 关键参数

### bits
- **4 bits**: 推荐，平衡精度和压缩
- **3 bits**: 极致压缩，精度下降
- **8 bits**: 几乎无损，压缩有限

### group_size
```python
# -1: 整个矩阵共享 scale（最大压缩）
# 32: 高精度，推理开销大
# 128: 推荐（平衡）
# 256: 较快推理，精度略降
```

### desc_act
```python
# True: 按激活幅度排序权重（更好精度）
# False: 保持原始顺序（更快推理）
# 推荐: False（除非极致精度）
```

### damp_percent
```python
# 阻尼 Hessian 矩阵避免数值不稳定
# 范围: 0.001 - 0.1
# 推荐: 0.01
```

## 与 AWQ 对比

### 量化方法
- **GPTQ**: 二阶优化，全局最优
- **AWQ**: 激活感知，启发式

### 量化速度
- **GPTQ**: 较慢 (~15min for 7B)
- **AWQ**: 较快 (~5min for 7B)

### 推理性能
- **GPTQ**: 略慢（复杂解量化）
- **AWQ**: 更快（简化计算）

### 精度
- **GPTQ**: 3-bit 可用
- **AWQ**: 主要 4-bit

### 选择建议
```
高精度优先 → GPTQ (支持3-bit)
速度优先 → AWQ
CPU推理 → GPTQ (更广泛支持)
GPU推理 → AWQ (Tensor Core优化)
```

## 部署场景

### 云端服务
```
场景: GPU 服务器批量推理
配置: GPTQ 4-bit, group_size=128
效果: 4× 内存节省, 2-3× 吞吐量
```

### 边缘设备
```
场景: 消费级 GPU (RTX 3060)
配置: GPTQ 4-bit, 小 group_size
效果: 13B 模型可运行
```

### 成本优化
```
场景: 降低云成本
策略: 用量化模型替代大规模部署
节省: 70-80% GPU 成本
```

## 最佳实践

### 1. 校准数据
```python
# 使用任务相关数据
calibration_data = [
    "example 1...",
    "example 2...",
    ...  # 128-512 samples
]

# 覆盖多样场景
# 长短文本均衡
# 代表真实分布
```

### 2. 量化后验证
```python
# 评估困惑度
eval_ppl(model_fp16, eval_data)
eval_ppl(model_gptq, eval_data)

# 下游任务测试
eval_accuracy(model_gptq, task_data)

# A/B 对比
compare_outputs(model_fp16, model_gptq)
```

### 3. 混合精度
```python
# 关键层保持高精度
sensitive_layers = ["lm_head", "embed_tokens"]

# 其他层激进量化
quantize_config = {
    "default": {"bits": 4, "group_size": 128},
    "sensitive": {"bits": 8, "group_size": 64}
}
```

## 工程考量

### 内存需求
```
量化过程:
- 原始模型: 需要加载 FP16
- Hessian 计算: 额外 10-20% 内存
- 建议: 2× 模型大小的 GPU 显存

推理阶段:
- 仅需量化模型
- 4× 压缩比
```

### 推理优化
```python
# 使用 Exllama 内核
model.config.use_exllama = True

# Marlin 格式（H100 优化）
model.config.use_marlin = True

# CUDA Graphs
model.config.use_cuda_graph = True
```

### 监控指标
- **量化时间**: 跟踪效率
- **模型大小**: 验证压缩比
- **推理速度**: 实际吞吐量
- **精度下降**: 可接受范围

## 研究方向

### GPTQ 变体
- **SpQR**: 稀疏量化
- **QuIP**: 梯度重参数化
- **OmniQuant**: 多目标优化

### 未来发展
1. **更低精度**: 2-bit, 1-bit
2. **混合精度**: 层/通道级别
3. **硬件协同**: 专用量化芯片
4. **端到端**: 训练+量化一体化


## 相关概念
- [[gguf]]

- [[awq]]
- [[kv-cache-quantization]]
