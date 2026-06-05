# 📚 学习路径

组织您的学习旅程、课程、技能发展和知识获取。

## 📖 进行中的学习

```dataview
TABLE type as "类型", progress as "进度", started as "开始日期", updated as "更新时间"
FROM "learning"
WHERE status = "in-progress"
SORT updated DESC
```

## 📝 课程笔记

```dataview
TABLE platform as "平台", instructor as "讲师", completed as "完成百分比"
FROM "learning"
WHERE type = "course"
SORT completed DESC
```

## 🎓 技能发展

```dataview
TABLE level as "水平", category as "类别", last_practiced as "最后练习"
FROM "learning"
WHERE type = "skill"
SORT level DESC, last_practiced DESC
```

## 📚 阅读清单

```dataview
TABLE author as "作者", status as "状态", rating as "评分"
FROM "learning"
WHERE type = "book"
SORT status ASC, rating DESC
```

## 🗂️ 学习分类

- **技术技能** — 编程、工具、技术
- **软技能** — 沟通、领导力、管理
- **语言** — 外语学习
- **创意** — 设计、写作、艺术
- **商业** — 创业、营销、财务
- **个人发展** — 生产力、习惯、心理学

---

[[README|← 返回首页]] | [[meta/dashboard|📊 仪表板]]
