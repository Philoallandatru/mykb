---
type: concept
category: 系统架构
source: LLM Serving技术对比分析
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - llm-serving
  - comparison
  - architecture
---

# vLLM vs SGLang 技术对比

## 💡 核心区别

> **vLLM更像"通用高吞吐LLM Serving Engine"，核心是PagedAttention + 连续批处理 + 生产生态；SGLang更像"面向复杂LLM程序/Agent/RAG工作流的Serving Runtime"，核心是RadixAttention + 结构化生成 + cache-aware调度。**

## 📝 详细对比

### 设计目标差异

#### vLLM: 高吞吐Serving Engine

**定位**:
- 把HuggingFace模型高效变成OpenAI-compatible服务
- 通用推理服务引擎

**适用模式**:
```
大量独立请求
  ↓
统一OpenAI API接入
  ↓
高吞吐serving
  ↓
多模型、多租户、K8s/生产部署
```

**核心能力**:
- PagedAttention
- Continuous batching
- Chunked prefill
- Prefix caching
- CUDA/HIP graphs
- 多种量化
- OpenAI-compatible API
- Structured outputs
- Tool calling

#### SGLang: LLM程序执行Runtime

**定位**:
- Frontend language + Runtime系统
- 高效执行复杂LLM程序

**适用模式**:
```
Agent / RAG / 多轮任务 / 多次LLM调用
  ↓
大量共享system prompt / few-shot / history prefix
  ↓
需要复用KV cache
  ↓
需要结构化输出、工具调用、并行分支
```

**核心能力**:
- RadixAttention
- Structured generation language
- Cache-aware load balancer
- Zero-overhead CPU scheduler
- Hierarchical KV cache

### 根本差异

```
vLLM: 把"单次/批量推理服务"做得很强
SGLang: 把"复杂LLM程序执行"做得很强
```

## 🔧 KV Cache机制对比

### vLLM: PagedAttention

**核心思想**: 类似操作系统分页

**工作方式**:
```
Token sequence
  ↓
固定大小KV blocks
  ↓
Block table / hash table
  ↓
复用相同prefix的block
```

**优势**:
- 避免显存碎片
- 高效管理长短请求混合
- 通用性强

**Prefix caching**:
- 基于hash table管理KV blocks
- 复用早期请求的缓存块
- Block-level粒度

### SGLang: RadixAttention

**核心思想**: Radix tree (压缩前缀树)

**工作方式**:
```
多个请求 / 多个LLM call
  ↓
共享system prompt / history / examples
  ↓
Radix tree管理公共prefix
  ↓
更细粒度复用KV
```

**优势**:
- 自然匹配多轮对话
- 更适合复杂workflow
- 细粒度prefix复用

**扩展**: HiCache
- 扩展到host memory
- 分布式storage支持

### 关键差异表

| 维度 | vLLM | SGLang |
|------|------|--------|
| KV基础思想 | PagedAttention | RadixAttention |
| Cache组织 | Block/hash管理 | Radix tree前缀树 |
| 最擅长 | 通用请求调度、显存高效利用 | 多调用、多分支、共享prefix复用 |
| 对RAG/Agent的意义 | 能复用prefix，serving engine视角 | 把cache reuse作为核心设计 |

## 🔗 相关概念

- [[vllm|vLLM系统]]
- [[kv-cache|KV缓存]]
- [[paged-attention|PagedAttention]]
- [[radix-attention|RadixAttention]]
- [[continuous-batching|连续批处理]]

## 📊 调度策略对比

### vLLM调度重点

**目标**: 高吞吐serving

**策略**:
- Continuous batching
- Chunked prefill
- Prefix caching
- Speculative decoding
- Disaggregated prefill/decode

**优化方向**:
```
如何把大量请求高效塞进GPU batch
```

**V1重构**:
- Scheduler优化
- KV cache manager重构
- Worker改进
- 降低CPU overhead

### SGLang调度重点

**目标**: Cache-aware + 低开销

**策略**:
- Zero-overhead CPU scheduler
- Cache-aware load balancer
- Hierarchical KV cache

**优化方向**:
```
如何减少CPU调度开销
如何让请求尽量命中已有KV cache
```

**Cache-aware load balancing**:
- 预测worker上的prefix KV cache hit rate
- 把请求路由到更可能命中的worker

## 💼 共同特性

### 功能重叠表

| 特性 | vLLM | SGLang |
|------|------|--------|
| OpenAI-compatible API | ✅ | ✅ |
| HuggingFace模型接入 | ✅ | ✅ |
| Continuous batching | ✅ | ✅ |
| Paged attention | ✅ | ✅ |
| Prefix caching | ✅ | ✅ (RadixAttention更突出) |
| Chunked prefill | ✅ | ✅ |
| Speculative decoding | ✅ | ✅ |
| Structured outputs | ✅ | ✅ |
| Tool calling | ✅ | ✅ |
| Quantization | FP8/INT8/INT4/AWQ/GPTQ/GGUF | FP4/FP8/INT4/AWQ/GPTQ |
| Tensor parallel | ✅ | ✅ |
| Pipeline parallel | ✅ | ✅ |
| MoE support | ✅ | ✅ |
| Multi-LoRA | ✅ | ✅ |
| Multimodal | ✅ | ✅ |
| Prefill/decode disaggregation | ✅ | ✅ |

### 关键差异

虽然功能重叠，但实现侧重点不同：

**vLLM**:
- Structured output是serving engine的高级功能
- 从通用服务角度设计

**SGLang**:
- Structured generation是核心设计目标
- 从LLM程序执行角度设计

## 🎯 使用场景选择

### 更适合vLLM的场景

✅ **场景特征**:
```
1. 标准OpenAI-compatible服务
2. 普通chat/completion/embedding服务
3. 大量相对独立的请求
4. 生产生态、文档、社区优先
5. K8s / Ray / 多卡部署
6. 需要稳定支持各种量化和模型格式
```

**典型应用**:
- 企业内部OpenAI API服务
- 对接Dify、LiteLLM、OpenWebUI
- 给Agent框架提供推理后端
- 多租户推理平台

### 更适合SGLang的场景

✅ **场景特征**:
```
1. Agent多步调用
2. RAG多轮检索生成
3. 长system prompt / few-shot prompt大量复用
4. 多分支并行generation
5. 强结构化输出、JSON、regex、EBNF
6. Cache-aware routing / prefix cache命中率优化
7. DeepSeek/Qwen等模型的特定优化
```

**典型应用**:
- Jira/Confluence知识库Agent
- 日志分析Agent
- 需求自动case生成
- 复杂RAG workflow
- 多轮对话系统

## 💡 选择决策树

### 核心判断标准

**请求特征判断**:
```
请求之间几乎没有共享上下文
  ↓
vLLM往往是默认选择

请求之间大量共享prefix / system prompt / few-shot
  ↓
SGLang更值得测试
```

**功能需求判断**:
```
你要的是标准serving
  ↓
vLLM

你要的是agentic workflow runtime
  ↓
SGLang
```

### 实际环境考虑

**本地开发**:
- 快速起OpenAI API → vLLM
- Qwen/DeepSeek + Agent + prefix cache → SGLang
- Windows本机 → LM Studio / llama.cpp
- WSL/Linux/Docker → vLLM或SGLang

**生产部署**:
- 多GPU高吞吐通用服务 → vLLM
- 特定模型 + 复杂workflow → SGLang

**集成需求**:
- LMCache / KV offload研究 → 都值得测
- 标准生态集成 → vLLM更成熟

## 📊 性能考量

### 不能简单说谁更快

性能取决于workload特征：

**vLLM优势场景**:
- 大量独立请求
- 通用batch调度
- 多样化模型支持

**SGLang优势场景**:
- 高prefix复用率
- 复杂多步workflow
- Cache-aware routing价值明显

### Benchmark考虑

对AI SSD / KV cache benchmark：

**vLLM workload代表**:
```
大量独立请求
PagedAttention block管理
Prefix cache
```

**SGLang workload代表**:
```
多轮/多分支请求
RadixAttention prefix tree
Cache-aware routing
高prefix reuse率
```

**建议**: 两者都纳入benchmark
- vLLM测通用LLM serving
- SGLang测高prefix reuse的RAG/Agent场景

## 🔍 API和使用方式

### 共同点

都支持OpenAI-compatible API：
- Completions
- Chat
- Embeddings
- Structured outputs
- Tool calling

### 差异点

**vLLM典型使用**:
```bash
vllm serve Qwen/Qwen2.5-7B-Instruct
```

**SGLang典型使用**:

方式1: Server模式
```bash
python -m sglang.launch_server --model-path ...
```

方式2: Native API (独特)
```python
# 用SGLang frontend language写复杂workflow
```

## 📚 参考资料

- [[vllm|vLLM系统详解]]
- [[kv-cache|KV缓存]]
- [[lmcache|LMCache]] - 可与两者集成
- [[.raw/llm-offloading-research-2026|Offloading技术综述]]

## 💭 个人理解

### 技术演进视角

两者代表了LLM serving的两条路线：

**通用化路线** (vLLM):
- 像Web Server一样服务各种模型
- 强调throughput、latency、resource efficiency
- 生态兼容性和稳定性优先

**专门化路线** (SGLang):
- 像Workflow Engine一样执行LLM程序
- 强调cache reuse、complex routing、structured generation
- Agent和RAG场景优先

### 实践建议

**开始阶段**:
- 先用vLLM (文档全、生态好)
- 验证基础功能

**优化阶段**:
- 分析实际workload
- 如果prefix复用率高，测试SGLang
- 对比实际性能

**生产阶段**:
- 根据主要场景选择
- 也可以混合部署（不同workload用不同引擎）

### 与其他技术的关系

**LMCache集成**:
- [[lmcache-stress-test-learning|LMCache实验]]基于vLLM
- SGLang也支持KV cache offloading
- 选择取决于主要框架

**GPU Direct Storage**:
- [[gpu-direct-storage|GDS]]对两者都适用
- 都可从SSD直接加载优化

**Offloading策略**:
- 两者架构影响offloading效果
- RadixAttention可能对distributed cache更友好

---

*创建于: 2026-06-04*
*来源: LLM Serving技术深度对比分析*
