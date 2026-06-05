# 💪 健康跟踪

跟踪您的健康、习惯、锻炼和营养。

## 🎯 活跃习惯

```dataview
TABLE streak as "连续天数", last_tracked as "最后记录", frequency as "频率"
FROM "health"
WHERE type = "habit" AND status = "active"
SORT streak DESC
```

## 🏃 锻炼日志

```dataview
TABLE type as "类型", duration as "时长", intensity as "强度", date as "日期"
FROM "health"
WHERE type = "workout"
SORT date DESC
LIMIT 10
```

## 🍎 营养笔记

```dataview
TABLE category as "类别", updated as "更新时间"
FROM "health"
WHERE type = "nutrition"
SORT updated DESC
```

## 📈 健康指标

```dataview
TABLE metric as "指标", value as "数值", date as "日期"
FROM "health"
WHERE type = "metric"
SORT date DESC
LIMIT 15
```

## 🗂️ 分类

- **习惯跟踪** — 日常习惯和连续记录
- **锻炼日志** — 训练记录和进度
- **营养** — 饮食计划和笔记
- **睡眠** — 睡眠质量和模式
- **心理健康** — 情绪、压力管理

---

[[README|← 返回首页]] | [[meta/dashboard|📊 仪表板]]
