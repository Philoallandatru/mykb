---
aliases:
- kv-cache-reuse
- prompt-caching
tags:
- llm-inference
- optimization
- caching
created: '2026-06-09'
---

# prefix-caching

## 定义

Prefix Caching 是一种优化技术，缓存和重用多个请求共享的 KV cache 前缀部分，避免重复计算相同的输入序列。

## 核心概念

### 问题背景
在 LLM 推理中，许多请求共享相同的前缀：
- **系统提示词**: 所有请求使用相同的 system prompt
- **Few-shot 示例**: 上下文学习的示例固定
- **RAG 检索结果**: 多个问题共享检索到的文档
- **对话历史**: 多轮对话逐渐累积相同历史

传统方式每个请求都独立计算整个序列，导致大量重复计算。

### Prefix Caching 解决方案
- **识别前缀**: 检测多个请求的公共前缀
- **缓存 KV**: 缓存前缀对应的 KV cache
- **重用计算**: 新请求直接使用缓存的 KV，只计算新部分
- **内存管理**: 智能管理缓存空间和淘汰策略

## 实现方式

### 1. 显式 Prefix Caching (vLLM)
```python
# 在 vLLM 中使用 prefix caching
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    enable_prefix_caching=True  # 启用 prefix caching
)

# 相同的 system prompt 会被缓存
system_prompt = "You are a helpful AI assistant..."

prompts = [
    system_prompt + "\nUser: Question 1",
    system_prompt + "\nUser: Question 2",  # 重用 system_prompt 的 KV
    system_prompt + "\nUser: Question 3",
]

outputs = llm.generate(prompts)
```

### 2. 自动 Prefix Caching (SGLang RadixAttention)
```python
# SGLang 自动识别和缓存前缀
import sglang as sgl

@sgl.function
def chat_with_system(s, user_msg):
    s += sgl.system("You are a helpful assistant.")  # 自动缓存
    s += sgl.user(user_msg)
    s += sgl.assistant(sgl.gen("response", max_tokens=256))

# 多次调用自动重用 system prompt 的 KV cache
for question in questions:
    chat_with_system.run(user_msg=question)
```

## 性能提升

### TTFT (Time To First Token)
- **无缓存**: 需要计算完整输入序列
- **有缓存**: 跳过前缀计算，直接从新部分开始
- **提升**: 50-90% TTFT 降低（取决于前缀长度）

### 吞吐量
- **减少计算**: 避免重复计算相同前缀
- **提升 GPU 利用率**: 更多资源用于新 token 生成
- **整体提升**: 2-5× 吞吐量（取决于重用率）

### 内存效率
- **KV cache 共享**: 多个请求共享相同前缀的 KV
- **内存节省**: 30-70%（取决于前缀占比和请求数）

## 缓存策略

### 前缀识别

#### 精确匹配
- 完全相同的 token 序列
- 最简单，最安全
- vLLM 默认策略

#### 语义匹配
- 基于语义相似度
- 更灵活，但可能有误差
- 研究阶段

### 淘汰策略

#### LRU (Least Recently Used)
- 淘汰最久未使用的 cache
- 简单有效
- 大多数系统默认

#### LFU (Least Frequently Used)
- 淘汰访问频率最低的 cache
- 适合长期运行服务

#### TTL (Time To Live)
- 设置缓存过期时间
- 防止陈旧数据占用空间

## 应用场景

### 1. 对话系统
**场景**: 所有对话使用相同 system prompt
```
System: You are a customer service assistant...  [CACHED]
User: What's your return policy?
Assistant: ...
User: How do I track my order?               [REUSE System]
Assistant: ...
```

**提升**: TTFT 降低 60-80%

### 2. Few-Shot Learning
**场景**: 固定的示例 + 不同的查询
```
[Example 1: ...]  [CACHED]
[Example 2: ...]  [CACHED]
[Example 3: ...]  [CACHED]
Query 1: ...
Query 2: ...      [REUSE Examples]
```

**提升**: 3-5× 吞吐量

### 3. RAG 系统
**场景**: 多个问题共享检索文档
```
Context: [Retrieved Document]  [CACHED]
Q1: Summarize the main points.
Q2: What about the methodology?  [REUSE Context]
Q3: Any limitations mentioned?   [REUSE Context]
```

**提升**: 2-4× 吞吐量

### 4. Agent 工作流
**场景**: Tool descriptions 缓存
```
Available Tools:
- search(query): ...    [CACHED]
- calculator(expr): ... [CACHED]
- translator(text): ... [CACHED]

Task 1: Search for Python tutorials
Task 2: Calculate 123 * 456        [REUSE Tools]
```

**提升**: Agent 响应速度提升 40-60%

## 实现考量

### 1. 缓存粒度
- **Token-level**: 精确匹配每个 token
- **Block-level**: PagedAttention 的块级别缓存
- **权衡**: 精度 vs 灵活性

### 2. 内存管理
- **最大缓存大小**: 限制总内存占用
- **淘汰策略**: 平衡命中率和内存
- **监控指标**: 跟踪命中率和内存使用

### 3. 并发控制
- **多请求共享**: 同时访问相同 cache
- **写时复制**: 避免缓存污染
- **锁机制**: 保证并发安全

## 配置示例

### vLLM 配置
```python
from vllm import LLM

llm = LLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    enable_prefix_caching=True,
    max_num_seqs=256,  # 增加并发支持更多重用
    block_size=16,     # 块大小影响缓存粒度
)
```

### SGLang 配置
```bash
python -m sglang.launch_server \
  --model-path meta-llama/Llama-2-7b-chat-hf \
  --enable-radix-cache \
  --max-radix-tree-size 8192
```

## 监控和调优

### 关键指标
- **Cache hit rate**: 缓存命中率（目标 > 60%）
- **TTFT reduction**: 首 token 延迟降低
- **Memory usage**: 缓存占用内存
- **Eviction rate**: 淘汰频率

### 优化建议
1. **识别常见前缀**: 分析请求模式
2. **调整缓存大小**: 平衡命中率和内存
3. **优化淘汰策略**: 根据访问模式选择
4. **监控命中率**: 持续跟踪和调整

## 限制和挑战

### 1. 冷启动
- 首次请求无法受益
- 需要预热期

### 2. 内存开销
- 缓存本身占用内存
- 需要权衡内存和计算

### 3. 缓存失效
- 模型更新后缓存失效
- 需要重新构建

### 4. 复杂度
- 增加系统实现复杂度
- 需要精心设计缓存策略

## 研究方向

1. **语义缓存**: 基于语义而非精确匹配
2. **分层缓存**: L1/L2 多级缓存
3. **自适应策略**: 根据负载动态调整
4. **跨模型共享**: 不同模型间共享缓存


## 相关概念

- [[sglang]]
- [[vllm]]
- [[kv-cache]]
