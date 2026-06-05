---
type: concept
category: 系统设计
source: Linux kernel, Tutti论文
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - io
  - async
  - performance
---

# io_uring

## 💡 定义

io_uring是Linux内核的高性能异步I/O接口，通过共享内存环形缓冲区实现零拷贝、零系统调用的I/O操作。

## 📝 详细说明

### 传统I/O的问题

**同步I/O (read/write)**:
- 阻塞式调用，线程等待I/O完成
- 每次调用都有系统调用开销

**异步I/O (libaio)**:
- 仅支持direct I/O
- API复杂且功能受限
- 仍需系统调用提交请求

### io_uring的创新

**核心设计**：
- **提交队列（SQ）** - 用户空间写入I/O请求
- **完成队列（CQ）** - 内核写入完成事件
- **共享内存** - 用户态和内核态共享ring buffer

**优势**：
1. **零系统调用** - 提交和完成都通过内存映射
2. **批量操作** - 一次提交多个I/O请求
3. **真正异步** - 支持所有I/O类型（文件、网络、定时器等）
4. **高效轮询** - 可选busy-polling模式

### API工作流

```c
// 1. 获取SQ条目
sqe = io_uring_get_sqe(&ring);

// 2. 准备I/O请求
io_uring_prep_read(sqe, fd, buffer, size, offset);

// 3. 提交请求（可批量）
io_uring_submit(&ring);

// 4. 等待完成
io_uring_wait_cqe(&ring, &cqe);

// 5. 处理结果
result = cqe->res;
io_uring_cqe_seen(&ring, &cqe);
```

## 🔗 相关概念

- [[Async-IO|异步I/O]]
- [[Zero-Copy|零拷贝]]
- [[Ring-Buffer|环形缓冲区]]
- [[GPU-io-uring|GPU io_uring]] - Tutti在GPU上的实现

## 💼 应用场景

### 高性能场景
- **数据库** - PostgreSQL、ScyllaDB已采用
- **网络服务器** - 处理大量并发连接
- **存储系统** - 高IOPS工作负载
- **GPU存储** - Tutti系统的核心技术

### 性能提升
- **延迟** - 减少50-70%的系统调用开销
- **吞吐量** - 批量提交提高2-3倍IOPS
- **CPU使用** - 降低30-40%的CPU占用

## 🔧 Tutti中的应用

Tutti将io_uring的设计移植到GPU：

**GPU io_uring**:
- SQ和CQ在GPU显存中
- GPU内核直接提交I/O请求
- CPU完全退出关键路径
- 实现GPU到SSD的零CPU干预I/O

**创新点**:
- 重构GPU存储栈
- GPU原生的I/O控制逻辑
- 与CUDA流集成

## 📚 参考资料

- [Linux io_uring官方文档](https://kernel.dk/io_uring.pdf)
- [liburing库](https://github.com/axboe/liburing)
- [[tutti-paper-2605.03375|Tutti论文]] - GPU上的实现

## 💭 关键优势

| 对比项 | 传统同步I/O | libaio | io_uring |
|--------|-------------|--------|----------|
| 系统调用 | 每次I/O一次 | 每批一次 | 可零次 |
| I/O类型 | 所有 | 仅direct I/O | 所有 |
| 批量提交 | ❌ | ✅ | ✅ |
| 真正异步 | ❌ | 部分 | ✅ |
| CPU效率 | 低 | 中 | 高 |

---

*创建于: 2026-06-04*
*来源: Tutti论文分析和Linux文档*
