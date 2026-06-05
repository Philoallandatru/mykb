# 📁 项目索引

管理您的所有项目、倡议和工作流。

## 🔥 活跃项目

```dataview
TABLE status as "状态", priority as "优先级", started as "开始日期", updated as "更新时间"
FROM "projects"
WHERE status = "active" OR status = "in-progress"
SORT priority DESC, updated DESC
```

## 📋 计划中的项目

```dataview
TABLE priority as "优先级", estimated_effort as "预计工作量"
FROM "projects"
WHERE status = "planned"
SORT priority DESC
```

## ✅ 已完成项目

```dataview
TABLE completed as "完成日期", outcome as "成果"
FROM "projects"
WHERE status = "completed"
SORT completed DESC
LIMIT 10
```

## 📊 按优先级

- **高优先级**: `= length(filter(file.lists, (x) => contains(x, "priority: high")))`
- **中优先级**: `= length(filter(file.lists, (x) => contains(x, "priority: medium")))`
- **低优先级**: `= length(filter(file.lists, (x) => contains(x, "priority: low")))`

---

[[README|← 返回首页]] | [[meta/dashboard|📊 仪表板]]
