# 🎯 目标跟踪

设定、跟踪和实现您的短期和长期目标。

## 🔥 活跃目标

```dataview
TABLE status as "状态", deadline as "截止日期", progress as "进度", category as "类别"
FROM "goals"
WHERE status = "active"
SORT deadline ASC
```

## 📅 本月目标

```dataview
TABLE progress as "进度", deadline as "截止日期"
FROM "goals"
WHERE deadline >= date(today) AND deadline <= date(today) + dur(30 days)
SORT deadline ASC
```

## 🌟 长期目标

```dataview
TABLE timeframe as "时间框架", progress as "进度", updated as "更新时间"
FROM "goals"
WHERE timeframe = "long-term" OR timeframe = "yearly"
SORT updated DESC
```

## ✅ 已完成目标

```dataview
TABLE completed as "完成日期", category as "类别", outcome as "成果"
FROM "goals"
WHERE status = "completed"
SORT completed DESC
LIMIT 10
```

## 📊 按类别

- **职业发展**
- **健康与健身**
- **学习与技能**
- **财务**
- **人际关系**
- **个人成长**

---

[[README|← 返回首页]] | [[meta/dashboard|📊 仪表板]]
