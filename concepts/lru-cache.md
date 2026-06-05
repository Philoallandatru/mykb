---
type: concept
category: 算法
source: 经典算法,LMCache实验
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - algorithm
  - caching
  - systems
---

# LRU缓存算法

## 💡 定义

LRU (Least Recently Used，最近最少使用) 是一种缓存驱逐策略，当缓存满时自动删除最久未被访问的数据，保留最近使用的热数据。

## 📝 详细说明

### 工作原理

**核心思想**: 如果数据最近被访问过，那么将来被访问的概率也更高。

**操作**:
1. **缓存命中** - 将访问的数据移到队列头部
2. **缓存未命中** - 加载数据并放到队列头部
3. **缓存满** - 删除队列尾部（最久未用）的数据

### 数据结构

经典实现使用 **哈希表 + 双向链表**:

```python
class LRUCache:
    def __init__(self, capacity):
        self.cache = {}  # 哈希表：O(1) 查找
        self.capacity = capacity
        self.head = Node()  # 双向链表
        self.tail = Node()
        
    def get(self, key):
        if key in self.cache:
            node = self.cache[key]
            self._move_to_head(node)  # 更新访问顺序
            return node.value
        return -1
    
    def put(self, key, value):
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            if len(self.cache) >= self.capacity:
                # 驱逐最久未用的
                removed = self._remove_tail()
                del self.cache[removed.key]
            
            new_node = Node(key, value)
            self.cache[key] = new_node
            self._add_to_head(new_node)
```

**时间复杂度**:
- Get: O(1)
- Put: O(1)
- Evict: O(1)

## 🔗 相关概念

- [[cache-replacement|缓存替换策略]]
- [[lfu-cache|LFU缓存]] - 按访问频率驱逐
- [[arc-cache|ARC缓存]] - 自适应替换
- [[two-queue|2Q算法]] - 两级队列

## 💼 应用场景

### 系统软件
- **操作系统** - 页面置换算法
- **数据库** - Buffer Pool管理
- **CDN** - 内容缓存
- **浏览器** - HTTP缓存

### LMCache中的应用

在LMCache磁盘缓存中的实际表现：

**测试场景**:
- 缓存上限: 20 GB
- 达到峰值: 19.64 GB (2,873 文件)
- 继续写入: 触发LRU驱逐

**驱逐效果**:
- 删除: 716 个旧文件
- 释放: 4.89 GB
- 最终: 14.75 GB (2,157 文件)
- 结果: ✅ 自动保持在容量限制内

**优势**:
- 无需手动清理缓存
- 热数据自动保留
- 冷数据自动驱逐

## 🎯 LRU的优缺点

### ✅ 优势
1. **简单高效** - O(1)时间复杂度
2. **实现直观** - 符合人类直觉
3. **自适应** - 自动适应访问模式
4. **广泛验证** - 几十年生产使用

### ❌ 局限
1. **顺序扫描问题** - 大量一次性访问会污染缓存
2. **周期性访问** - 访问周期 > 缓存容量时失效
3. **不考虑频率** - 偶尔一次访问和频繁访问同等对待
4. **突发流量** - 可能错误驱逐重要数据

### 改进方案

**LRU-K**: 考虑最近K次访问历史
**2Q**: 区分短期和长期访问
**ARC**: 自适应平衡LRU和LFU
**Clock**: 近似LRU，更低开销

## 🔍 实际案例分析

### LMCache LRU驱逐日志

```text
初始: 19.64 GB (2873 文件)
写入新缓存...
触发驱逐: 删除 716 个旧文件
最终: 14.75 GB (2157 文件)
```

**分析**:
- 驱逐率: 24.9% (716/2873)
- 释放空间: 4.89 GB
- 保留: 75.1% 热数据

**这说明**:
- ✅ LRU准确识别了冷数据
- ✅ 大部分数据仍在被使用（保留75%）
- ✅ 自动腾出空间给新数据

### 为什么加速比下降？

从56x → 1.08x的原因：

```text
阶段1: 同一prompt重复50次
→ 缓存命中率: ~100%
→ LRU保留所有数据
→ 加速: 56x

阶段2: 80个不同prompts
→ 缓存命中率: 低
→ LRU频繁驱逐
→ warm cache变cold cache
→ 加速: 1.08x
```

**启示**: LRU在高重复场景最优，低重复场景收益有限。

## 📊 性能对比

| 策略 | Get | Put | 命中率 | 内存 |
|------|-----|-----|--------|------|
| LRU | O(1) | O(1) | 中等 | 中等 |
| LFU | O(log n) | O(log n) | 高 | 高 |
| FIFO | O(1) | O(1) | 低 | 低 |
| Random | O(1) | O(1) | 低 | 低 |

## 💭 个人理解

### 何时选择LRU

**适合**:
- 访问模式有时间局部性
- 热数据集相对稳定
- 需要简单高效的实现
- 大多数Web应用、数据库

**不适合**:
- 大量顺序扫描（如日志分析）
- 周期性访问（如定时任务）
- 需要更精细控制（如优先级缓存）

### 工程实践

1. **监控命中率** - 低于80%考虑调整策略
2. **预热缓存** - 启动时加载热数据
3. **分层缓存** - L1用LRU，L2用其他策略
4. **容量规划** - 工作集 < 缓存容量

## 📚 参考资料

- [[cache-algorithms|缓存算法综述]]
- [[lmcache|LMCache]] - 实际应用案例
- [[.raw/lmcache-multi-ssd-stress-test|LRU驱逐实验观察]]

---

*创建于: 2026-06-04*
*来源: LMCache实验观察 + 经典算法*
