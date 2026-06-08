#!/usr/bin/env python3
"""
知识库批量内容摄取工具
用于批量注入文档、笔记和概念到知识库
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml

class KnowledgeBaseIngester:
    """知识库内容摄取器"""

    def __init__(self, kb_root: str = "/home/ficus/code/mykb"):
        self.kb_root = Path(kb_root)
        self.raw_dir = self.kb_root / ".raw"
        self.concepts_dir = self.kb_root / "concepts"
        self.learning_dir = self.kb_root / "learning"
        self.entities_dir = self.kb_root / "entities"
        self.meta_dir = self.kb_root / "meta"

        # 确保目录存在
        for d in [self.raw_dir, self.concepts_dir, self.learning_dir,
                  self.entities_dir, self.meta_dir]:
            d.mkdir(exist_ok=True)

    def ingest_from_json(self, json_file: str):
        """从JSON配置文件批量摄取内容

        JSON格式示例:
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
                    "links": {"website": "https://..."}
                }
            ],
            "learning_notes": [
                {
                    "name": "学习笔记标题",
                    "content": "学习笔记内容...",
                    "insights": ["洞察1", "洞察2"],
                    "tags": ["tag1"]
                }
            ]
        }
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        report = {
            "source": data.get("source", "未知来源"),
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "type": data.get("type", "内容摄取"),
            "files_created": [],
            "stats": {
                "raw": 0,
                "concepts": 0,
                "entities": 0,
                "learning": 0
            }
        }

        # 1. 保存原始内容
        if "raw_content" in data:
            raw = data["raw_content"]
            filename = self._sanitize_filename(raw["filename"])
            filepath = self.raw_dir / filename
            self._write_file(filepath, raw["content"])
            report["files_created"].append(str(filepath.relative_to(self.kb_root)))
            report["stats"]["raw"] += 1

        # 2. 创建概念笔记
        for concept in data.get("concepts", []):
            filepath = self._create_concept(concept)
            report["files_created"].append(str(filepath.relative_to(self.kb_root)))
            report["stats"]["concepts"] += 1

        # 3. 创建实体笔记
        for entity in data.get("entities", []):
            filepath = self._create_entity(entity)
            report["files_created"].append(str(filepath.relative_to(self.kb_root)))
            report["stats"]["entities"] += 1

        # 4. 创建学习笔记
        for note in data.get("learning_notes", []):
            filepath = self._create_learning_note(note)
            report["files_created"].append(str(filepath.relative_to(self.kb_root)))
            report["stats"]["learning"] += 1

        # 5. 生成摄取报告
        report_file = self._generate_report(data, report)

        return report_file

    def ingest_from_directory(self, dir_path: str, file_pattern: str = "*.md"):
        """从目录批量摄取markdown文件到.raw/"""
        import glob

        dir_path = Path(dir_path)
        files = glob.glob(str(dir_path / file_pattern))

        report = {
            "source": f"目录: {dir_path}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "批量文件摄取",
            "files_created": [],
            "stats": {"raw": 0}
        }

        for file in files:
            filename = Path(file).name
            dest = self.raw_dir / filename

            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()

            self._write_file(dest, content)
            report["files_created"].append(str(dest.relative_to(self.kb_root)))
            report["stats"]["raw"] += 1

        # 生成简单报告
        report_name = f"ingestion-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        report_file = self.meta_dir / report_name

        report_content = f"""# 批量文件摄取报告

**日期**: {report["date"]}
**来源**: {report["source"]}
**文件数**: {report["stats"]["raw"]}

## 摄取的文件

"""
        for f in report["files_created"]:
            report_content += f"- `{f}`\n"

        self._write_file(report_file, report_content)

        return report_file

    def _create_concept(self, concept: Dict) -> Path:
        """创建概念笔记"""
        name = self._sanitize_filename(concept["name"])
        filepath = self.concepts_dir / f"{name}.md"

        # 构建frontmatter
        frontmatter = {
            "aliases": concept.get("aliases", []),
            "tags": concept.get("tags", []),
            "created": datetime.now().strftime("%Y-%m-%d")
        }

        content = "---\n"
        content += yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        content += "---\n\n"
        content += f"# {concept['name']}\n\n"
        content += concept["content"]

        # 添加相关链接
        if "related" in concept and concept["related"]:
            content += "\n\n## 相关概念\n\n"
            for rel in concept["related"]:
                content += f"- [[{rel}]]\n"

        self._write_file(filepath, content)
        return filepath

    def _create_entity(self, entity: Dict) -> Path:
        """创建实体笔记"""
        name = self._sanitize_filename(entity["name"])
        filepath = self.entities_dir / f"{name}.md"

        frontmatter = {
            "type": entity.get("type", "未分类"),
            "tags": entity.get("tags", []),
            "created": datetime.now().strftime("%Y-%m-%d")
        }

        if "links" in entity:
            frontmatter["links"] = entity["links"]

        content = "---\n"
        content += yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        content += "---\n\n"
        content += f"# {entity['name']}\n\n"
        content += entity["content"]

        self._write_file(filepath, content)
        return filepath

    def _create_learning_note(self, note: Dict) -> Path:
        """创建学习笔记"""
        name = self._sanitize_filename(note["name"])
        filepath = self.learning_dir / f"{name}.md"

        frontmatter = {
            "tags": note.get("tags", []),
            "created": datetime.now().strftime("%Y-%m-%d")
        }

        content = "---\n"
        content += yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        content += "---\n\n"
        content += f"# {note['name']}\n\n"
        content += note["content"]

        # 添加洞察部分
        if "insights" in note and note["insights"]:
            content += "\n\n## 核心洞察\n\n"
            for i, insight in enumerate(note["insights"], 1):
                content += f"{i}. {insight}\n"

        self._write_file(filepath, content)
        return filepath

    def _generate_report(self, data: Dict, report: Dict) -> Path:
        """生成摄取报告"""
        source_slug = self._sanitize_filename(data.get("source", "unknown"))
        report_name = f"ingestion-report-{source_slug}.md"
        report_file = self.meta_dir / report_name

        content = f"""# {data.get('source', '内容摄取')}报告

**日期**: {report['date']}
**来源**: {report['source']}
**类型**: {report['type']}

---

## 📥 摄取统计

- 原始文件: {report['stats']['raw']}
- 概念笔记: {report['stats']['concepts']}
- 实体笔记: {report['stats']['entities']}
- 学习笔记: {report['stats']['learning']}
- **总计**: {sum(report['stats'].values())}

## 📁 创建的文件

"""

        for f in report["files_created"]:
            content += f"- `{f}`\n"

        content += f"\n\n---\n\n**摄取完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        self._write_file(report_file, content)
        return report_file

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名"""
        # 移除或替换不安全字符
        name = name.lower()
        name = name.replace(" ", "-")
        name = name.replace("/", "-")
        name = name.replace("\\", "-")
        name = name.replace(":", "")
        name = name.replace("*", "")
        name = name.replace("?", "")
        name = name.replace('"', "")
        name = name.replace("<", "")
        name = name.replace(">", "")
        name = name.replace("|", "")
        return name

    def _write_file(self, filepath: Path, content: str):
        """写入文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ 创建: {filepath.relative_to(self.kb_root)}")


def main():
    parser = argparse.ArgumentParser(description="知识库批量内容摄取工具")
    parser.add_argument("--json", help="从JSON配置文件摄取")
    parser.add_argument("--dir", help="从目录批量摄取markdown文件")
    parser.add_argument("--pattern", default="*.md", help="文件匹配模式（配合--dir使用）")
    parser.add_argument("--kb-root", default="/home/ficus/code/mykb", help="知识库根目录")

    args = parser.parse_args()

    ingester = KnowledgeBaseIngester(args.kb_root)

    if args.json:
        print(f"📥 从JSON配置摄取: {args.json}")
        report_file = ingester.ingest_from_json(args.json)
        print(f"\n✅ 摄取完成！报告: {report_file}")

    elif args.dir:
        print(f"📥 从目录批量摄取: {args.dir}")
        report_file = ingester.ingest_from_directory(args.dir, args.pattern)
        print(f"\n✅ 摄取完成！报告: {report_file}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
