#!/usr/bin/env bash
# 知识库工具快速参考

cat << 'EOF'
📚 知识库批量摄取工具 - 快速参考
═══════════════════════════════════════

🔧 核心工具
───────────

1. batch_ingest.py - 批量摄取内容
   python3 scripts/batch_ingest.py --json config.json
   python3 scripts/batch_ingest.py --dir /path/to/docs

2. analyze_kb.py - 分析知识库
   python3 scripts/analyze_kb.py                    # 完整报告
   python3 scripts/analyze_kb.py --check-links      # 检查损坏的链接
   python3 scripts/analyze_kb.py --find-orphans     # 查找孤立笔记

3. repair_links.py - 修复链接
   python3 scripts/repair_links.py integrate 笔记名 相关1 相关2
   python3 scripts/repair_links.py fix 文件 旧链接 新链接
   python3 scripts/repair_links.py list             # 列出所有笔记

4. quick_ingest.sh - 交互式摄取
   bash scripts/quick_ingest.sh

📋 典型工作流
─────────────

# 步骤 1: 创建 JSON 配置
cp scripts/template.json my-content.json
vim my-content.json

# 步骤 2: 执行摄取
python3 scripts/batch_ingest.py --json my-content.json

# 步骤 3: 整合到知识网络
python3 scripts/repair_links.py integrate 新笔记 相关笔记1 相关笔记2

# 步骤 4: 验证质量
python3 scripts/analyze_kb.py

# 步骤 5: 提交到 git
git add .
git commit -m "Add new content: [描述]"

📄 文档位置
───────────

- 完整使用指南: scripts/README.md
- 配置模板: scripts/template.json
- 示例配置: scripts/example_config.json
- 部署报告: meta/batch-ingestion-deployment-report.md

🎯 快速示例
───────────

# 添加一个新概念
cat > /tmp/new-concept.json << 'EXAMPLE'
{
  "source": "快速添加",
  "date": "2026-06-08",
  "type": "概念",
  "concepts": [
    {
      "name": "新概念名称",
      "content": "## 概述\n\n详细内容...",
      "tags": ["tag1", "tag2"],
      "related": ["相关概念1"]
    }
  ]
}
EXAMPLE

python3 scripts/batch_ingest.py --json /tmp/new-concept.json

📊 当前状态
───────────

知识库统计 (最后更新: 2026-06-08):
  - 总笔记数: 53
  - 概念: 13 | 实体: 7 | 学习: 10
  - 平均链接数: 5.97
  - 网络连通性: 70%

EOF
