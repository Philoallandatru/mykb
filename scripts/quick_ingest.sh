#!/usr/bin/env bash
# 快速摄取工具 - 交互式创建摄取配置

set -e

KB_ROOT="/home/ficus/code/mykb"
SCRIPT_DIR="$KB_ROOT/scripts"

echo "📚 知识库批量摄取工具"
echo "======================="
echo

# 选择摄取模式
echo "选择摄取模式："
echo "1) 从 JSON 配置文件"
echo "2) 从目录批量导入"
echo "3) 交互式创建（概念笔记）"
echo

read -p "请选择 (1-3): " mode

case $mode in
  1)
    read -p "JSON 配置文件路径: " json_path
    if [ ! -f "$json_path" ]; then
      echo "❌ 文件不存在: $json_path"
      exit 1
    fi
    python3 "$SCRIPT_DIR/batch_ingest.py" --json "$json_path"
    ;;

  2)
    read -p "目录路径: " dir_path
    if [ ! -d "$dir_path" ]; then
      echo "❌ 目录不存在: $dir_path"
      exit 1
    fi
    read -p "文件匹配模式 (默认 *.md): " pattern
    pattern=${pattern:-"*.md"}
    python3 "$SCRIPT_DIR/batch_ingest.py" --dir "$dir_path" --pattern "$pattern"
    ;;

  3)
    echo
    echo "🎯 交互式创建概念笔记"
    echo "----------------------"

    read -p "概念名称: " concept_name
    read -p "概念简介: " concept_desc
    read -p "标签 (逗号分隔): " tags
    read -p "相关概念 (逗号分隔): " related

    # 转换标签和相关概念为数组
    IFS=',' read -ra tag_array <<< "$tags"
    IFS=',' read -ra related_array <<< "$related"

    # 生成 JSON
    temp_json="/tmp/quick_ingest_$$.json"

    cat > "$temp_json" << EOF
{
  "source": "交互式创建",
  "date": "$(date +%Y-%m-%d)",
  "type": "概念笔记",
  "concepts": [
    {
      "name": "$concept_name",
      "content": "## 概述\n\n$concept_desc\n\n## 详细说明\n\n(待补充)\n",
      "aliases": [],
      "tags": [$(printf '"%s",' "${tag_array[@]}" | sed 's/,$//')],
      "related": [$(printf '"%s",' "${related_array[@]}" | sed 's/,$//')]
    }
  ],
  "entities": [],
  "learning_notes": []
}
EOF

    echo
    echo "📋 生成的配置:"
    cat "$temp_json"
    echo

    read -p "确认摄取? (y/n): " confirm
    if [ "$confirm" = "y" ]; then
      python3 "$SCRIPT_DIR/batch_ingest.py" --json "$temp_json"
      rm "$temp_json"
    else
      echo "❌ 已取消"
      rm "$temp_json"
      exit 1
    fi
    ;;

  *)
    echo "❌ 无效选择"
    exit 1
    ;;
esac

echo
echo "✅ 摄取完成！"
echo
echo "查看结果:"
echo "  cd $KB_ROOT"
echo "  git status"
echo
echo "提交到 git:"
echo "  git add ."
echo "  git commit -m 'Add new content'"
