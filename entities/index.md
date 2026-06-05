# 👥 实体索引

人物、工具、资源和地点。

## 分类

### 人物

```dataview
TABLE role as "角色", relationship as "关系", last_contact as "最后联系"
FROM "entities"
WHERE type = "person"
SORT last_contact DESC
```

### 工具

```dataview
TABLE category as "类别", status as "状态", rating as "评分"
FROM "entities"
WHERE type = "tool"
SORT rating DESC
```

### 资源

```dataview
TABLE type as "类型", url as "链接", added as "添加日期"
FROM "entities"
WHERE type = "resource"
SORT added DESC
```

---

[[README|← 返回首页]]
