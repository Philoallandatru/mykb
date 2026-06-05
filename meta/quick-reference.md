# 快速参考

## 📝 常用模板

在Obsidian中创建新笔记时，从 `_templates/` 文件夹选择模板：

- `project.md` — 项目管理
- `goal.md` — 目标设定
- `learning-note.md` — 学习笔记
- `health-log.md` — 健康记录
- `entity.md` — 实体（人物/工具/资源）
- `concept.md` — 概念和想法

## 🔗 双链语法

```markdown
[[笔记名称]]              # 基本链接
[[笔记名称|显示文本]]      # 自定义显示文本
![[笔记名称]]             # 嵌入整个笔记
![[图片.png]]             # 嵌入图片
[[笔记名称#标题]]         # 链接到特定章节
```

## 🏷️ 标签系统

使用标签组织内容：

```markdown
#project/work
#goal/health
#learning/programming
#concept/productivity
```

## ⌨️ 快捷键

- `Ctrl/Cmd + N` — 新建笔记
- `Ctrl/Cmd + O` — 快速打开
- `Ctrl/Cmd + P` — 命令面板
- `Ctrl/Cmd + E` — 切换编辑/预览模式
- `Ctrl/Cmd + ,` — 设置
- `Ctrl/Cmd + Shift + F` — 全局搜索

## 📊 Dataview查询示例

```dataview
TABLE status, priority, deadline
FROM "projects"
WHERE status = "active"
SORT priority DESC
```

## 🎯 最佳实践

1. **原子笔记** — 每个笔记专注于一个想法
2. **使用双链** — 建立知识网络
3. **添加frontmatter** — 使笔记可搜索和可查询
4. **定期回顾** — 每周查看仪表板
5. **保持收件箱清空** — 处理 `.raw/` 文件夹内容

---

[[README|← 返回首页]]
