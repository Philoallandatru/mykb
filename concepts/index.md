# 💡 概念索引

想法、原则、框架和方法论。

## 最近概念

```dataview
TABLE category as "类别", source as "来源", created as "创建日期"
FROM "concepts"
SORT created DESC
LIMIT 20
```

## 按类别

```dataview
TABLE count(rows) as "数量"
FROM "concepts"
GROUP BY category
SORT count(rows) DESC
```

## 标签云

常用标签会在这里出现。

---

[[README|← 返回首页]]
