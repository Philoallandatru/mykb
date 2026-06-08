---
aliases:
- speculative-sampling
- draft-verification
tags:
- llm-inference
- optimization
- acceleration
created: '2026-06-09'
---

# speculative-decoding

## 定义

Speculative Decoding（推测解码）是一种 LLM 推理加速技术，使用小型高速 draft 模型预测多个 token，然后由大型目标模型并行验证，在保持输出质量的同时提升生成速度。

## 核心原理

### 传统自回归解码问题
```
每次只生成1个token:
T1 → T2 → T3 → T4 → ...
每步都需要完整的模型前向传播
```

**瓶颈**:
- 每个 token 生成需要一次完整推理
- GPU 利用率低（内存带宽瓶颈）
- 生成速度慢（序列长度正比）

### Speculative Decoding 解决方案

**两阶段流程**:

#### 1. Draft 阶段（小模型）
```
快速生成 K 个候选 token:
T1 → T2 → T3 → ... → TK
使用小型模型（如 7B）
```

#### 2. Verification 阶段（大模型）
```
并行验证所有候选:
[T1, T2, T3, ..., TK] → 一次前向传播
使用目标模型（如 70B）
接受正确的 token，拒绝错误的
```

**关键**: 并行验证多个 token，摊销大模型的推理成本

## 工作流程

### 详细步骤

1. **Draft**: 小模型自回归生成 K 个 token
   ```
   draft_tokens = []
   for i in range(K):
       token = draft_model.generate_next()
       draft_tokens.append(token)
   ```

2. **Verify**: 大模型并行计算概率
   ```
   # 一次前向传播计算所有位置的概率
   probs = target_model.forward(draft_tokens)
   ```

3. **Accept/Reject**: 基于概率比较决定接受
   ```
   for i, token in enumerate(draft_tokens):
       p_draft = draft_model.prob(token)
       p_target = target_model.prob(token)
       
       if random() < min(1, p_target / p_draft):
           accept(token)  # 接受
       else:
           reject(token)  # 拒绝，从目标模型采样
           break
   ```

4. **Continue**: 从第一个拒绝位置继续

## 加速原理

### 并行验证的优势
- **批量计算**: K 个 token 一次计算
- **摊销成本**: 大模型推理成本 / K
- **保持质量**: 输出分布与原始模型一致

### 加速比计算
```
Speedup = (接受的token数 + 1) / (draft次数 + verify次数)

理想情况（所有接受）:
  K个draft + 1次verify = K+1 tokens
  Speedup = (K+1) / (K+1) ≈ K（当K大时）

实际情况（接受率 α）:
  期望token数 = α × K
  Speedup ≈ α × K / (K + 1)
```

**示例**:
- K=4, α=0.7: Speedup ≈ 2.24×
- K=8, α=0.5: Speedup ≈ 2.67×

## 实现变体

### 1. 标准 Speculative Decoding
- **Draft模型**: 独立训练的小模型
- **验证**: 基于概率比较
- **优点**: 通用，适用任何模型对
- **缺点**: 需要额外的小模型

### 2. Speculative Sampling
- **改进**: 无偏采样算法
- **保证**: 输出分布严格等同目标模型
- **方法**: 修正的接受-拒绝采样

### 3. Medusa
- **Draft**: 多头并行预测
- **结构**: 目标模型 + 轻量预测头
- **优点**: 无需独立小模型
- **加速**: 2-3× 实际加速

### 4. Lookahead Decoding
- **策略**: 使用 n-gram 预测
- **无需模型**: 基于统计规律
- **适用**: 有重复模式的文本

## 关键参数

### 1. Draft 长度 (K)
- **小K (2-4)**: 接受率高，加速有限
- **大K (8-16)**: 接受率低，可能降低效率
- **最优**: 通常 K=4-8

### 2. 模型选择

#### Draft 模型要求
- **速度**: 至少比目标模型快 3-5×
- **质量**: 接受率 > 50%
- **大小**: 通常 7B vs 70B

#### 常见配置
| 目标模型 | Draft 模型 | 接受率 | 加速比 |
|---------|-----------|--------|--------|
| LLaMA-70B | LLaMA-7B | 60-70% | 2-3× |
| GPT-4 | GPT-3.5 | 50-60% | 1.5-2× |

### 3. 温度和采样
- **温度**: 影响接受率
  - 低温 (0.1): 接受率高
  - 高温 (1.0): 接受率低
- **Top-p/Top-k**: 需要在 draft 和 target 保持一致

## 性能分析

### 加速场景
✓ **高接受率任务**: 翻译、摘要、代码生成
✓ **低温采样**: 确定性输出
✓ **长序列**: 摊销验证成本
✓ **批次小**: draft 模型开销相对小

### 不适用场景
✗ **创意生成**: 高温采样，接受率低
✗ **完全随机**: draft 模型无法预测
✗ **极短序列**: 验证开销占比高
✗ **大批次**: draft 模型成为瓶颈

### 实测数据
```
任务: 代码生成 (HumanEval)
模型对: Codex-13B + Codex-1.3B
K=4, 温度=0.2

结果:
- 接受率: 74%
- 加速比: 2.8×
- 输出质量: 完全一致
```

## 实现挑战

### 1. 模型对齐
- **问题**: draft 和 target 模型需要对齐
- **解决**: 
  - 使用相同 tokenizer
  - Draft 模型蒸馏自 target
  - Fine-tune draft 模型提高接受率

### 2. 内存管理
- **问题**: 同时加载两个模型
- **解决**:
  - Draft 模型量化（INT8/INT4）
  - 共享 Embedding 层
  - 分时加载（仅 draft 时卸载 target）

### 3. KV Cache 管理
- **问题**: 需要管理两个模型的 KV cache
- **解决**:
  - 预分配 cache 空间
  - Draft cache 可以丢弃
  - Target cache 持久保存

## 工程实践

### vLLM 集成
```python
from vllm import LLM, SamplingParams

# 配置 speculative decoding
sampling_params = SamplingParams(
    use_beam_search=False,
    speculative_decoding=True,
    draft_model="meta-llama/Llama-2-7b-hf",
    num_speculative_tokens=5,
)

llm = LLM(model="meta-llama/Llama-2-70b-hf")
outputs = llm.generate(prompts, sampling_params)
```

### 监控指标
- **接受率**: accepted_tokens / draft_tokens
- **实际加速**: wall_clock_speedup
- **内存占用**: draft_memory + target_memory

### 调优建议
1. **测试接受率**: 不同 K 值和温度
2. **Profile**: 确认 draft 模型不是瓶颈
3. **任务适配**: 选择高接受率的任务
4. **模型蒸馏**: 提升 draft 质量

## 研究方向

### 1. 自适应 K 选择
- 根据接受率动态调整 draft 长度
- 不同任务使用不同策略

### 2. 多级 Draft
- 使用多个中间模型
- 渐进式验证

### 3. 树状解码
- Draft 生成多个候选分支
- Target 模型选择最佳路径

### 4. 硬件优化
- 专用硬件加速 draft 模型
- 重叠 draft 和 verify 计算

## 论文和资源

- **Fast Inference from Transformers via Speculative Decoding** (2023)
- **Accelerating Large Language Model Decoding with Speculative Sampling** (2023)
- **Medusa: Simple Framework for Accelerating LLM Generation** (2024)


## 相关概念

- [[vllm]]
- [[sglang]]
