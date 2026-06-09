---
type: entity
entity_type: tool
category: 机器学习框架
created: 2026-06-04
updated: 2026-06-04
tags:
  - entity
  - tool
  - llm
  - inference
---
	
# vLLM

## 📋 基本信息

**类型**: LLM推理引擎  
**类别**: 开源软件  
**开发者**: UC Berkeley Sky Computing Lab  
**网站**: https://github.com/vllm-project/vllm

## 📝 描述

vLLM (Virtual LLM) 是一个高性能、易用的大语言模型推理和服务引擎，专为生产环境设计。

### 核心特性

**PagedAttention**:
- 创新的KV缓存管理算法
- 类似操作系统的虚拟内存分页
- 消除内存碎片化
- 提高GPU利用率

**性能优势**:
- 比HuggingFace Transformers快 **24倍**
- 比传统方案高 **2-4倍** 吞吐量
- 支持连续批处理（continuous batching）

**易用性**:
- 兼容HuggingFace模型
- 简单的Python API
- OpenAI兼容的API服务器

### 最新集成

**Tutti集成** (2026):
- 支持SSD-backed KV缓存
- GPU中心的I/O架构
- 长上下文推理优化

## 🔗 相关笔记

### 相关技术
- [[inference-frameworks-ai-ssd]]
- [[flashinfer-jit-cache-best-practices]]
- [[tensorrt-llm]]
- [[speculative-decoding]]
- [[prefix-caching]]
- [[sglang]]
- [[tensor-parallelism]]
- [[flash-attention]]
- [[continuous-batching]]
- [[flashinfer]]
- [[flashinfer-jit-cache]]
- [[kv-cache|KV缓存]]
- [[paged-attention|PagedAttention]]
- [[tutti|Tutti系统]] - 最新集成

### 替代方案
- [[tgi|Text Generation Inference]] (HuggingFace)
- [[tensorrt-llm|TensorRT-LLM]] (NVIDIA)
- [[llamacpp|llama.cpp]] (轻量级)

## 💼 应用场景

### 生产环境
- **API服务** - OpenAI兼容端点
- **批量推理** - 大规模文本生成
- **实时对话** - 聊天机器人后端

### 研究场景
- **长上下文实验** - 结合Tutti
- **性能基准测试**
- **模型服务优化**

## 🎯 关键优势

| 特性 | vLLM | 传统方案 |
|------|------|---------|
| 吞吐量 | 高（2-4x） | 基准 |
| 内存效率 | PagedAttention | 静态分配 |
| 长上下文 | Tutti支持 | 内存受限 |
| 易用性 | 简单API | 复杂配置 |

## 💭 使用笔记

### 安装
```bash
pip install vllm
```

### 基础使用
```python
from vllm import LLM, SamplingParams

llm = LLM(model="meta-llama/Llama-2-7b-hf")
prompts = ["Hello, my name is"]
outputs = llm.generate(prompts)
```

### 启动服务器
```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-hf
```

---

*创建于: 2026-06-04*
*来源: Tutti论文和vLLM文档*
