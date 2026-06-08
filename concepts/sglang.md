---
aliases:
- structured-generation-language
- radixattention
tags:
- llm-inference
- prefix-caching
- structured-generation
created: '2026-06-09'
---

# sglang

## 定义

SGLang (Structured Generation Language) 是一个用于高效 LLM 推理和编程的开源框架，由 UC Berkeley 和 Stanford 开发，专注于结构化生成和复杂 AI 工作流。

## 核心特性

### 1. RadixAttention
- **核心创新**: 自动化的 KV cache 重用机制
- **基于前缀树**: 使用 Radix Tree 数据结构管理 KV cache
- **自动缓存共享**: 相同前缀的请求自动共享 KV cache
- **命中率**: 生产环境可达 80%+ prefix cache 命中率

### 2. 结构化生成
- **受约束解码**: 支持 JSON schema、正则表达式约束
- **语法引导**: 确保输出符合预定义格式
- **应用场景**: API 调用、结构化数据提取、代码生成

### 3. 编程接口
- **DSL (Domain Specific Language)**: 直观的 Python 风格 API
- **多轮对话**: 原生支持复杂对话流程
- **流式输出**: 高效的 streaming 支持

## 与 vLLM 对比

### 相同点
- 都使用 PagedAttention 进行内存管理
- 都支持 continuous batching
- 都集成 FlashAttention 等优化内核

### 差异点

| 特性 | vLLM | SGLang |
|------|------|--------|
| Prefix Caching | 手动配置 | RadixAttention 自动 |
| 结构化生成 | 有限支持 | 原生支持 |
| 编程接口 | OpenAI API | SGLang DSL + OpenAI API |
| 多轮对话 | 需手动管理状态 | 原生支持 |
| 适用场景 | 高吞吐推理 | 复杂 AI workflow |

## RadixAttention 技术细节

### 数据结构
```
Radix Tree (前缀树):
  root
  ├─ "Explain" (KV cached)
  │  ├─ " quantum" → " computing" (共享 "Explain")
  │  └─ " the" → " history" (共享 "Explain")
  └─ "Translate" (KV cached)
     └─ " to" → " Chinese" (共享 "Translate")
```

### 工作原理
1. 新请求到达时，查找 radix tree 匹配最长前缀
2. 重用匹配前缀的 KV cache
3. 只计算未缓存的新 token
4. 自动插入新分支到 radix tree

### 内存管理
- **LRU 淘汰**: 自动淘汰最少使用的分支
- **引用计数**: 跟踪 KV cache 块的引用
- **内存限制**: 可配置最大 cache 大小

## 性能优势

### 吞吐量
- **相比 vLLM**: 在有 prefix 重用的场景下提升 1.5-3×
- **相比无缓存**: 提升 5-10× (取决于 prefix 长度)

### 延迟
- **TTFT (Time To First Token)**: 显著降低（跳过已缓存部分）
- **整体延迟**: prefix 重用率高时降低 30-70%

### 内存效率
- **KV cache 共享**: 多个请求共享相同前缀
- **自动管理**: 无需手动配置共享策略

## 应用场景

### 1. 多轮对话
- 系统提示词自动缓存
- 对话历史渐进式扩展
- 上下文学习（few-shot）自动重用

### 2. Agent 系统
- Tool descriptions 缓存
- Chain-of-thought prompt 重用
- 多步骤推理流程

### 3. RAG (Retrieval-Augmented Generation)
- 检索到的文档作为 prefix
- 多个问题共享相同检索结果
- 知识库内容缓存

### 4. 批量处理
- 相同指令模板
- 不同数据点批量处理
- 系统级提示词共享

## 实现细节

### 安装和使用
```bash
# 安装
pip install sglang

# 启动服务
python -m sglang.launch_server \
  --model-path meta-llama/Llama-2-7b-chat-hf \
  --port 30000
```

### 编程接口
```python
import sglang as sgl

@sgl.function
def multi_turn_chat(s, question1, question2):
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question1)
    s += sgl.assistant(sgl.gen("answer1", max_tokens=256))
    s += sgl.user(question2)
    s += sgl.assistant(sgl.gen("answer2", max_tokens=256))

# 执行
state = multi_turn_chat.run(
    question1="What is SGLang?",
    question2="How does RadixAttention work?"
)
```

## 配置和调优

### RadixAttention 配置
```python
# 启动时配置
--enable-radix-cache          # 启用 RadixAttention
--max-radix-tree-size 8192    # 最大 tree 节点数
--cache-eviction-policy lru   # 淘汰策略
```

### 监控指标
- **Cache hit rate**: prefix cache 命中率
- **Tree size**: radix tree 节点数
- **Memory usage**: KV cache 内存占用

## 限制和注意事项

### 1. 内存开销
- Radix tree 本身有内存开销
- 需要足够内存存储 tree 结构

### 2. 适用场景
- 高 prefix 重复率时效果最好
- 完全随机请求提升有限

### 3. 复杂度
- Tree 管理增加系统复杂度
- 需要调优 eviction 策略

## 研究和发展

- **论文**: "Efficiently Programming Large Language Models using SGLang" (2024)
- **GitHub**: https://github.com/sgl-project/sglang
- **文档**: https://sgl-project.github.io/

## 与其他技术的关系

- **FlashInfer**: SGLang 使用 FlashInfer 作为 attention 后端
- **vLLM**: 可以互补使用，SGLang 专注于编程接口
- **Prefix Caching**: RadixAttention 是自动化的 prefix caching


## 相关概念
- [[speculative-decoding]]

- [[vllm]]
- [[flashinfer]]
- [[prefix-caching]]
