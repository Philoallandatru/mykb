#!/usr/bin/env python3
"""
知识库链接修复工具
用于建立新笔记与现有笔记之间的双向链接
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set
import argparse


class LinkRepairer:
    """链接修复器"""

    def __init__(self, kb_root: str = "/home/ficus/code/mykb"):
        self.kb_root = Path(kb_root)
        self.concepts_dir = self.kb_root / "concepts"
        self.learning_dir = self.kb_root / "learning"
        self.entities_dir = self.kb_root / "entities"

    def add_backlinks(self, source_file: str, target_file: str):
        """在目标文件中添加反向链接"""
        source_path = self._find_file(source_file)
        target_path = self._find_file(target_file)

        if not source_path or not target_path:
            print(f"⚠️  无法找到文件: {source_file} 或 {target_file}")
            return False

        content = target_path.read_text(encoding='utf-8')

        # 检查是否已经有这个链接
        if f"[[{source_path.stem}]]" in content:
            print(f"  ℹ️  {target_file} 已包含到 {source_file} 的链接")
            return False

        # 在文件末尾添加相关链接部分
        if "## 相关" not in content and "## Related" not in content:
            content += f"\n\n## 相关概念\n\n- [[{source_path.stem}]]\n"
        else:
            # 在相关部分添加链接
            content = re.sub(
                r'(## 相关.*?\n)',
                f'\\1- [[{source_path.stem}]]\n',
                content,
                count=1
            )

        target_path.write_text(content, encoding='utf-8')
        print(f"  ✓ 在 {target_file} 中添加了到 {source_file} 的链接")
        return True

    def create_related_section(self, file_path: str, related_links: List[str]):
        """在文件中创建或更新相关链接部分"""
        path = self._find_file(file_path)
        if not path:
            print(f"⚠️  无法找到文件: {file_path}")
            return False

        content = path.read_text(encoding='utf-8')

        # 移除现有的相关部分
        content = re.sub(r'\n## 相关.*?(?=\n##|\Z)', '', content, flags=re.DOTALL)

        # 添加新的相关部分
        if related_links:
            related_section = "\n\n## 相关概念\n\n"
            for link in related_links:
                related_section += f"- [[{link}]]\n"
            content += related_section

        path.write_text(content, encoding='utf-8')
        print(f"  ✓ 更新了 {file_path} 的相关链接")
        return True

    def fix_broken_link(self, file_path: str, old_link: str, new_link: str):
        """修复损坏的链接"""
        path = self._find_file(file_path)
        if not path:
            print(f"⚠️  无法找到文件: {file_path}")
            return False

        content = path.read_text(encoding='utf-8')
        old_pattern = f"[[{old_link}]]"
        new_pattern = f"[[{new_link}]]"

        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            path.write_text(content, encoding='utf-8')
            print(f"  ✓ 在 {file_path} 中修复了链接: {old_link} → {new_link}")
            return True
        else:
            print(f"  ℹ️  在 {file_path} 中未找到链接 {old_link}")
            return False

    def integrate_new_note(self, note_name: str, related_notes: List[str]):
        """将新笔记整合到知识网络中"""
        print(f"\n🔗 整合笔记: {note_name}")
        print(f"   相关笔记: {', '.join(related_notes)}")
        print()

        # 1. 在新笔记中创建相关链接
        self.create_related_section(note_name, related_notes)

        # 2. 在相关笔记中添加反向链接
        for related in related_notes:
            self.add_backlinks(note_name, related)

    def _find_file(self, filename: str) -> Path:
        """查找文件（支持不带扩展名）"""
        if not filename.endswith('.md'):
            filename += '.md'

        for directory in [self.concepts_dir, self.entities_dir, self.learning_dir]:
            path = directory / filename
            if path.exists():
                return path

        return None

    def list_all_notes(self) -> List[str]:
        """列出所有笔记（不含扩展名）"""
        notes = []
        for directory in [self.concepts_dir, self.entities_dir, self.learning_dir]:
            if directory.exists():
                notes.extend([f.stem for f in directory.glob("*.md")])
        return sorted(notes)


def main():
    parser = argparse.ArgumentParser(description="知识库链接修复工具")
    parser.add_argument("--kb-root", default="/home/ficus/code/mykb", help="知识库根目录")

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # integrate 命令
    integrate_parser = subparsers.add_parser('integrate', help='整合新笔记到知识网络')
    integrate_parser.add_argument('note', help='笔记名称')
    integrate_parser.add_argument('related', nargs='+', help='相关笔记列表')

    # fix 命令
    fix_parser = subparsers.add_parser('fix', help='修复损坏的链接')
    fix_parser.add_argument('file', help='文件名')
    fix_parser.add_argument('old_link', help='旧链接')
    fix_parser.add_argument('new_link', help='新链接')

    # backlink 命令
    backlink_parser = subparsers.add_parser('backlink', help='添加反向链接')
    backlink_parser.add_argument('source', help='源文件')
    backlink_parser.add_argument('target', help='目标文件')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有笔记')

    args = parser.parse_args()

    repairer = LinkRepairer(args.kb_root)

    if args.command == 'integrate':
        repairer.integrate_new_note(args.note, args.related)

    elif args.command == 'fix':
        repairer.fix_broken_link(args.file, args.old_link, args.new_link)

    elif args.command == 'backlink':
        repairer.add_backlinks(args.source, args.target)

    elif args.command == 'list':
        notes = repairer.list_all_notes()
        print("所有笔记:")
        for note in notes:
            print(f"  - {note}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
