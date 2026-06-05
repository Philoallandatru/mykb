# 📊 仪表板

*您的个人第二大脑概览*

---

## 🎯 活跃目标

```dataview
TABLE status as "状态", deadline as "截止日期", progress as "进度"
FROM "goals"
WHERE status = "active"
SORT deadline ASC
LIMIT 5
```

## 📁 进行中的项目

```dataview
TABLE status as "状态", priority as "优先级", updated as "更新时间"
FROM "projects"
WHERE status = "active" OR status = "in-progress"
SORT priority DESC, updated DESC
LIMIT 10
```

## 📚 最近学习

```dataview
TABLE type as "类型", status as "状态", updated as "更新时间"
FROM "learning"
SORT updated DESC
LIMIT 8
```

## 💪 健康习惯

```dataview
TABLE streak as "连续天数", last_tracked as "最后记录"
FROM "health"
WHERE type = "habit"
SORT streak DESC
```

## 📝 最近笔记

```dataview
TABLE file.mtime as "修改时间"
FROM ""
WHERE file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 15
```

## 🔗 待处理内容

```dataview
TABLE file.size as "大小", file.ctime as "创建时间"
FROM ".raw"
SORT file.ctime DESC
```

---

## 📈 统计

- **总笔记数**: `= length(filter(file.lists, (x) => x))`
- **实体数**: `= length(filter(file.lists, (x) => contains(x.path, "entities")))`
- **概念数**: `= length(filter(file.lists, (x) => contains(x.path, "concepts")))`
- **项目数**: `= length(filter(file.lists, (x) => contains(x.path, "projects")))`

---

*更新于: `= date(today)`*
