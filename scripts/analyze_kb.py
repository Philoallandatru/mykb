#!/usr/bin/env python3
"""
知识库统计和验证工具
用于查看知识库内容统计、验证链接完整性
"""

import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set
import argparse


class KnowledgeBaseAnalyzer:
    """知识库分析器"""

    def __init__(self, kb_root: str = "/home/ficus/code/mykb"):
        self.kb_root = Path(kb_root)
        self.concepts_dir = self.kb_root / "concepts"
        self.learning_dir = self.kb_root / "learning"
        self.entities_dir = self.kb_root / "entities"
        self.raw_dir = self.kb_root / ".raw"
        self.meta_dir = self.kb_root / "meta"

    def get_statistics(self) -> Dict:
        """获取知识库统计信息"""
        stats = {
            "concepts": self._count_files(self.concepts_dir),
            "entities": self._count_files(self.entities_dir),
            "learning": self._count_files(self.learning_dir),
            "raw": self._count_files(self.raw_dir),
            "meta": self._count_files(self.meta_dir),
        }
        stats["total"] = sum(stats.values())
        return stats

    def _count_files(self, directory: Path, pattern: str = "*.md") -> int:
        """统计目录中的文件数"""
        if not directory.exists():
            return 0
        return len(list(directory.glob(pattern)))

    def analyze_links(self) -> Dict:
        """分析知识库中的链接关系"""
        all_files = []
        all_files.extend(self.concepts_dir.glob("*.md"))
        all_files.extend(self.entities_dir.glob("*.md"))
        all_files.extend(self.learning_dir.glob("*.md"))

        # 提取所有文件名（不含扩展名）
        file_names = {f.stem for f in all_files}

        # 分析链接
        links = defaultdict(set)
        broken_links = defaultdict(set)

        for file in all_files:
            content = file.read_text(encoding='utf-8')
            # 匹配 [[链接]]
            matches = re.findall(r'\[\[([^\]]+)\]\]', content)

            for match in matches:
                # 去除可能的别名 [[link|alias]]
                link = match.split('|')[0].strip()

                links[file.stem].add(link)

                # 检查链接是否存在
                if link not in file_names and not self._is_special_link(link):
                    broken_links[file.stem].add(link)

        return {
            "total_links": sum(len(v) for v in links.values()),
            "files_with_links": len(links),
            "broken_links": dict(broken_links),
            "broken_count": sum(len(v) for v in broken_links.values()),
            "link_graph": dict(links)
        }

    def _is_special_link(self, link: str) -> bool:
        """检查是否为特殊链接（目录、索引等）"""
        special_patterns = [
            "/", "index", "dashboard", "changelog"
        ]
        return any(pattern in link for pattern in special_patterns)

    def analyze_tags(self) -> Dict:
        """分析标签使用情况"""
        all_files = []
        all_files.extend(self.concepts_dir.glob("*.md"))
        all_files.extend(self.entities_dir.glob("*.md"))
        all_files.extend(self.learning_dir.glob("*.md"))

        tag_counts = Counter()
        files_by_tag = defaultdict(list)

        for file in all_files:
            content = file.read_text(encoding='utf-8')

            # 从 frontmatter 提取标签
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                # 匹配 tags: [tag1, tag2] 或 tags: 形式
                tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
                if tags_match:
                    tags_str = tags_match.group(1)
                    tags = [t.strip().strip('"\'') for t in tags_str.split(',') if t.strip()]

                    for tag in tags:
                        tag_counts[tag] += 1
                        files_by_tag[tag].append(file.stem)

        return {
            "total_tags": len(tag_counts),
            "total_usages": sum(tag_counts.values()),
            "top_tags": tag_counts.most_common(10),
            "files_by_tag": dict(files_by_tag)
        }

    def find_orphans(self) -> List[str]:
        """找到孤立的笔记（没有被其他笔记引用）"""
        all_files = []
        all_files.extend(self.concepts_dir.glob("*.md"))
        all_files.extend(self.entities_dir.glob("*.md"))
        all_files.extend(self.learning_dir.glob("*.md"))

        file_names = {f.stem for f in all_files}
        referenced = set()

        for file in all_files:
            content = file.read_text(encoding='utf-8')
            matches = re.findall(r'\[\[([^\]]+)\]\]', content)

            for match in matches:
                link = match.split('|')[0].strip()
                if link in file_names:
                    referenced.add(link)

        orphans = file_names - referenced
        return sorted(orphans)

    def generate_report(self):
        """生成完整的分析报告"""
        print("=" * 60)
        print("📊 知识库分析报告")
        print("=" * 60)
        print()

        # 1. 基本统计
        print("## 📁 文件统计")
        print()
        stats = self.get_statistics()
        print(f"  概念笔记 (concepts):    {stats['concepts']:>4}")
        print(f"  实体笔记 (entities):    {stats['entities']:>4}")
        print(f"  学习笔记 (learning):    {stats['learning']:>4}")
        print(f"  原始内容 (.raw):        {stats['raw']:>4}")
        print(f"  元数据 (meta):          {stats['meta']:>4}")
        print(f"  " + "-" * 30)
        print(f"  总计:                   {stats['total']:>4}")
        print()

        # 2. 链接分析
        print("## 🔗 链接分析")
        print()
        link_analysis = self.analyze_links()
        print(f"  总链接数:               {link_analysis['total_links']:>4}")
        print(f"  有链接的文件:           {link_analysis['files_with_links']:>4}")
        print(f"  损坏的链接:             {link_analysis['broken_count']:>4}")
        print()

        if link_analysis['broken_links']:
            print("  ⚠️  损坏的链接详情:")
            for file, broken in sorted(link_analysis['broken_links'].items())[:10]:
                print(f"    {file}:")
                for link in sorted(broken):
                    print(f"      → [[{link}]]")
            if len(link_analysis['broken_links']) > 10:
                print(f"    ... 还有 {len(link_analysis['broken_links']) - 10} 个文件")
        print()

        # 3. 标签分析
        print("## 🏷️  标签统计")
        print()
        tag_analysis = self.analyze_tags()
        print(f"  不同标签数:             {tag_analysis['total_tags']:>4}")
        print(f"  标签使用总数:           {tag_analysis['total_usages']:>4}")
        print()

        if tag_analysis['top_tags']:
            print("  📌 Top 10 标签:")
            for tag, count in tag_analysis['top_tags']:
                print(f"    {tag:<30} {count:>3}")
        print()

        # 4. 孤立笔记
        print("## 🏝️  孤立笔记 (未被引用)")
        print()
        orphans = self.find_orphans()
        if orphans:
            print(f"  共 {len(orphans)} 个孤立笔记:")
            for orphan in orphans[:20]:
                print(f"    - {orphan}")
            if len(orphans) > 20:
                print(f"    ... 还有 {len(orphans) - 20} 个")
        else:
            print("  ✅ 没有孤立笔记！")
        print()

        # 5. 知识网络密度
        print("## 📊 知识网络指标")
        print()
        total_notes = stats['concepts'] + stats['entities'] + stats['learning']
        if total_notes > 0:
            avg_links = link_analysis['total_links'] / total_notes
            connectivity = (total_notes - len(orphans)) / total_notes * 100
            print(f"  平均每篇笔记链接数:     {avg_links:.2f}")
            print(f"  网络连通性:             {connectivity:.1f}%")
        print()

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="知识库统计和验证工具")
    parser.add_argument("--kb-root", default="/home/ficus/code/mykb", help="知识库根目录")
    parser.add_argument("--check-links", action="store_true", help="只检查损坏的链接")
    parser.add_argument("--list-tags", action="store_true", help="列出所有标签")
    parser.add_argument("--find-orphans", action="store_true", help="查找孤立笔记")

    args = parser.parse_args()

    analyzer = KnowledgeBaseAnalyzer(args.kb_root)

    if args.check_links:
        link_analysis = analyzer.analyze_links()
        if link_analysis['broken_links']:
            print("⚠️  发现损坏的链接:")
            for file, broken in sorted(link_analysis['broken_links'].items()):
                print(f"\n{file}:")
                for link in sorted(broken):
                    print(f"  → [[{link}]]")
        else:
            print("✅ 所有链接都有效！")

    elif args.list_tags:
        tag_analysis = analyzer.analyze_tags()
        print("标签列表:")
        for tag, count in sorted(tag_analysis['top_tags'], key=lambda x: -x[1]):
            print(f"  {tag:<30} ({count} 次)")

    elif args.find_orphans:
        orphans = analyzer.find_orphans()
        if orphans:
            print(f"发现 {len(orphans)} 个孤立笔记:")
            for orphan in orphans:
                print(f"  - {orphan}")
        else:
            print("✅ 没有孤立笔记！")

    else:
        analyzer.generate_report()


if __name__ == "__main__":
    main()
