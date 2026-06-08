# 知识库批量摄取工具使用指南

## 概述

`batch_ingest.py` 是一个用于批量注入内容到知识库的自动化工具，支持从 JSON 配置文件或目录批量导入内容。

## 功能特性

- ✅ 从 JSON 配置文件批量创建笔记
- ✅ 从目录批量导入 markdown 文件
- ✅ 自动生成 frontmatter 和元数据
- ✅ 建立交叉引用和知识连接
- ✅ 生成详细的摄取报告
- ✅ 支持多种笔记类型（概念、实体、学习笔记、原始内容）

## 快速开始

### 方式 1: 从 JSON 配置文件摄取

```bash
# 基本用法
python3 scripts/batch_ingest.py --json scripts/example_config.json

# 指定知识库路径
python3 scripts/batch_ingest.py --json config.json --kb-root /path/to/kb
```

### 方式 2: 从目录批量导入

```bash
# 导入目录中的所有 markdown 文件到 .raw/
python3 scripts/batch_ingest.py --dir /path/to/documents

# 指定文件匹配模式
python3 scripts/batch_ingest.py --dir /path/to/documents --pattern "*.txt"
```

## JSON 配置文件格式

### 完整示例

```json
{
  "source": "来源描述",
  "date": "2026-06-08",
  "type": "技术分析",
  "raw_content": {
    "filename": "原始文档.md",
    "content": "完整的原始内容..."
  },
  "concepts": [
    {
      "name": "概念名称",
      "content": "概念的详细内容...",
      "aliases": ["别名1", "别名2"],
      "tags": ["tag1", "tag2"],
      "related": ["相关概念1", "相关概念2"]
    }
  ],
  "entities": [
    {
      "name": "实体名称",
      "type": "工具/框架/系统",
      "content": "实体的详细内容...",
      "tags": ["tag1"],
      "links": {
        "website": "https://...",
        "github": "https://github.com/..."
      }
    }
  ],
  "learning_notes": [
    {
      "name": "学习笔记标题",
      "content": "学习笔记内容...",
      "insights": [
        "洞察1",
        "洞察2"
      ],
      "tags": ["tag1"]
    }
  ]
}
```

### 字段说明

#### 顶层字段
- `source`: 内容来源描述
- `date`: 摄取日期 (YYYY-MM-DD)
- `type`: 内容类型

#### raw_content（原始内容）
- `filename`: 文件名
- `content`: 完整内容

#### concepts（概念笔记）
- `name`: 概念名称
- `content`: 概念详细内容
- `aliases`: 别名列表（可选）
- `tags`: 标签列表（可选）
- `related`: 相关概念列表（可选）

#### entities（实体笔记）
- `name`: 实体名称
- `type`: 实体类型（如"工具"、"框架"、"系统"）
- `content`: 实体详细内容
- `tags`: 标签列表（可选）
- `links`: 相关链接字典（可选）

#### learning_notes（学习笔记）
- `name`: 笔记标题
- `content`: 笔记内容
- `insights`: 核心洞察列表（可选）
- `tags`: 标签列表（可选）

## 使用场景

### 场景 1: 摄取技术文档

```json
{
  "source": "Kubernetes 官方文档",
  "date": "2026-06-08",
  "type": "技术文档",
  "concepts": [
    {
      "name": "pod",
      "content": "## Pod 是什么\n\nPod 是 Kubernetes 中最小的可部署单元...",
      "tags": ["kubernetes", "container"],
      "related": ["container", "deployment"]
    }
  ]
}
```

### 场景 2: 摄取研究论文

```json
{
  "source": "FlashAttention 论文",
  "date": "2026-06-08",
  "type": "学术论文",
  "raw_content": {
    "filename": "flash-attention-paper.md",
    "content": "# FlashAttention: Fast and Memory-Efficient Exact Attention..."
  },
  "concepts": [
    {
      "name": "flash-attention",
      "content": "一种快速且内存高效的 attention 算法...",
      "tags": ["attention", "transformer"]
    }
  ],
  "learning_notes": [
    {
      "name": "flash-attention-insights",
      "content": "## 核心创新\n\n1. Tiling 技术...",
      "insights": [
        "通过 tiling 减少 HBM 访问",
        "IO-aware 算法设计"
      ]
    }
  ]
}
```

### 场景 3: 批量导入已有文档

```bash
# 将整个目录的文档导入到 .raw/
python3 scripts/batch_ingest.py --dir ~/Documents/notes

# 之后可以手动处理 .raw/ 中的文件
```

## 输出结果

### 创建的文件

执行摄取后，会创建以下文件：

```
.raw/                          # 原始内容
├── flashinfer-jit-cache-analysis.md

concepts/                      # 概念笔记
├── flashinfer-jit-cache.md

entities/                      # 实体笔记  
├── flashinfer.md

learning/                      # 学习笔记
├── flashinfer-jit-cache-best-practices.md

meta/                          # 摄取报告
├── ingestion-report-flashinfer-jit-cache-技术分析.md
```

### 摄取报告

每次摄取都会在 `meta/` 目录生成详细报告，包含：

- 摄取统计
- 创建的文件列表
- 时间戳

## 最佳实践

### 1. 组织内容结构

在创建 JSON 配置前，先规划内容结构：

- **原始内容**: 完整保留原始信息
- **概念笔记**: 提取核心概念和定义
- **实体笔记**: 记录工具、框架、系统
- **学习笔记**: 总结洞察和最佳实践

### 2. 建立知识连接

充分利用 `related` 字段建立概念间的连接：

```json
{
  "name": "kv-cache",
  "related": ["flashinfer-jit-cache", "gpu-memory", "llm-inference"]
}
```

### 3. 使用有意义的标签

标签应该：
- 具体且有区分度
- 反映技术栈层次
- 便于后续过滤和检索

```json
{
  "tags": ["llm-inference", "cuda", "jit", "performance-optimization"]
}
```

### 4. 记录洞察而非事实

学习笔记的 `insights` 应该是：
- **Why**: 为什么这样做
- **How to apply**: 如何应用到实践中

```json
{
  "insights": [
    "JIT 缓存是动态编译和静态编译之间的最佳平衡点",
    "生产环境必须预热缓存，避免首个用户请求的编译延迟"
  ]
}
```

### 5. 版本控制

所有摄取的内容都会进入 git 仓库，记得：

```bash
# 查看新增内容
git status

# 提交摄取结果
git add .
git commit -m "Add FlashInfer JIT Cache content"
```

## 高级用法

### 批量处理多个配置

```bash
# 批量摄取多个 JSON 文件
for config in configs/*.json; do
    python3 scripts/batch_ingest.py --json "$config"
done
```

### 集成到自动化流程

```bash
#!/bin/bash
# auto_ingest.sh

# 1. 从外部源获取内容
curl https://api.example.com/content > /tmp/content.json

# 2. 转换为摄取配置
python3 convert_to_config.py /tmp/content.json > /tmp/ingest_config.json

# 3. 执行摄取
python3 scripts/batch_ingest.py --json /tmp/ingest_config.json

# 4. 自动提交
cd /home/ficus/code/mykb
git add .
git commit -m "Auto ingest: $(date +%Y-%m-%d)"
```

## 故障排查

### 问题 1: 权限错误

```bash
# 确保脚本可执行
chmod +x scripts/batch_ingest.py

# 检查目录权限
ls -la /home/ficus/code/mykb
```

### 问题 2: JSON 格式错误

```bash
# 验证 JSON 格式
python3 -m json.tool config.json
```

### 问题 3: 文件名冲突

工具会覆盖已存在的同名文件，建议：
- 使用唯一的文件名
- 提交前检查 `git diff`

## 扩展开发

### 添加新的笔记类型

编辑 `batch_ingest.py`，添加类似的方法：

```python
def _create_project(self, project: Dict) -> Path:
    """创建项目笔记"""
    name = self._sanitize_filename(project["name"])
    filepath = self.projects_dir / f"{name}.md"
    
    # ... 实现逻辑
    
    return filepath
```

### 自定义模板

在 `_templates/` 目录创建模板，在生成文件时应用。

## 参考资料

- 知识库结构说明: `../README.md`
- Obsidian 文档: https://obsidian.md
- 示例配置: `example_config.json`

---

**维护者**: Ficus  
**最后更新**: 2026-06-08  
**工具版本**: 1.0.0
