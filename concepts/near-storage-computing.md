---
type: concept
category: 系统架构
source: Offloading研究综述 2026
created: 2026-06-04
updated: 2026-06-04
tags:
  - concept
  - storage
  - computing
  - ai-hardware
---

# 近存储计算 (Near-Storage Computing)

## 💡 定义

近存储计算（Near-Storage Computing）是将计算能力部署在存储设备附近或内部，在数据所在位置直接进行处理，减少数据在存储与计算单元间的搬运开销。

## 📝 详细说明

### 传统范式 vs 近存储范式

**传统计算架构**:
```
数据存储 → PCIe搬运 → 主机内存 → 计算单元 → 结果返回
```
- 优势: 计算能力强大、灵活性高
- 劣势: PCIe带宽瓶颈、延迟高、能耗大

**近存储计算架构**:
```
数据存储 → 存储设备内部计算 → 小结果返回
```
- 优势: 内部高带宽、低延迟、减少PCIe流量
- 劣势: 计算能力受限、灵活性较低

### 核心思想

**数据重力定律** (Data Gravity):
> 当数据量足够大时，移动计算比移动数据更经济

**适用场景判断**:
```
数据量 × 传输成本 > 计算复杂度 × 本地计算成本
  ↓
适合近存储计算
```

### 在LLM推理中的应用

**问题场景**:
```
长上下文推理 (100K tokens)
  ↓
KV cache: 几百MB到几GB
  ↓
传统方案: 完整KV从SSD → GPU
  ↓
PCIe成为瓶颈 (8-16 GB/s vs SSD内部100+ GB/s)
```

**近存储解决方案**:
```
SSD/SmartSSD内部:
  - 存储完整KV cache
  - 执行token importance评估
  - 执行partial attention
  - 只返回top-K结果 (几十KB)
    ↓
PCIe流量减少 1000× 以上
GPU只做final attention
```

## 🔗 相关概念

- [[in-storage-processing|存内处理]]
- [[smartssd|SmartSSD]]
- [[computational-storage|计算型存储]]
- [[data-gravity|数据重力]]
- [[cxl-pnm|CXL Processing Near Memory]]

## 💼 应用场景

### 1. LLM KV Cache处理

**代表工作**:
- **InstInfer** - CSD内部做attention，13B模型提升11.1×
- **HILOS** - 近存储加速器，7.86× throughput，85% 能耗降低
- **HillInfer** - SmartSSD内做KV eviction和token evaluation

**收益分析**:
```
原始方案:
  SSD读15K tokens KV → 500 MB
  PCIe传输 → 60ms @ 8GB/s
  GPU attention → 10ms
  总计: 70ms

InstInfer:
  SSD内部partial attention → 40ms
  返回top-K结果 → 50 KB
  PCIe传输 → 0.006ms
  GPU final attention → 5ms
  总计: 45ms (1.5× 加速)
  
实际收益更大因为:
  - PCIe带宽节省给其他数据
  - GPU bubble time降低
  - 批处理效率提升
```

### 2. RAG系统

**传统流程**:
```
Query → Embedding
  ↓
搜索100GB向量索引 (在SSD)
  ↓
所有候选向量 → Host memory (几GB)
  ↓
CPU/GPU做相似度计算
  ↓
返回top-K
```

**近存储优化**:
```
Query → Embedding
  ↓
SSD内部做向量搜索
  ↓
只返回top-K向量 (几MB)
  ↓
GPU做精细排序
```

### 3. 数据分析

**场景**: 大规模日志分析、数据过滤、聚合

**传统方案**: 全部数据读到内存 → 过滤 → 处理
**近存储方案**: SSD内部过滤 → 只搬运匹配数据

### 4. 数据库查询

**SmartSSD + 数据库**:
- 谓词下推 (Predicate Pushdown)
- 投影下推 (Projection Pushdown)
- 聚合下推 (Aggregation Pushdown)

## 🔧 实现形态

### 1. SmartSSD

**架构**:
```
Host ↔ NVMe Controller ↔ FPGA/ARM Cores ↔ NAND Flash
```

**代表产品**:
- Samsung SmartSSD
- Xilinx (AMD) SmartSSD
- NGD Systems Catalina

**编程模型**:
- OpenCL kernels (FPGA)
- eBPF programs
- 自定义命令集

### 2. DPU (Data Processing Unit)

**例子**: NVIDIA BlueField DPU

**能力**:
- 网络加速
- 存储虚拟化
- 安全/加密
- Near-data processing

### 3. CSD (Computational Storage Drive)

**标准**: SNIA Computational Storage架构

**特点**:
- 标准化接口
- 应用无感知
- Kernel offload

### 4. Processing-Near-Memory (PNM)

**例子**: CXL-attached memory + accelerator

**适用**: 更通用的内存计算场景

## 🎯 优势与挑战

### ✅ 优势

1. **带宽优势**
   - SSD内部带宽 >> PCIe带宽
   - NAND channel并行度高

2. **延迟降低**
   - 无PCIe往返
   - 数据locality优秀

3. **能耗降低**
   - 减少PCIe传输能耗
   - 减少host CPU/GPU参与

4. **可扩展性**
   - 计算随存储扩展
   - 无中心化瓶颈

### ❌ 挑战

1. **计算能力受限**
   - FPGA/ARM性能 << GPU/CPU
   - 复杂算法难以实现

2. **编程复杂**
   - 需要专门编程模型
   - 调试困难

3. **标准化缺失**
   - 各厂商接口不同
   - 生态碎片化

4. **成本**
   - SmartSSD比普通SSD贵
   - 开发成本高

5. **适用场景有限**
   - 只适合可分解的操作
   - 不适合需要全局视图的算法

## 📊 性能对比

| 指标 | 传统SSD | SmartSSD | 理论提升 |
|------|---------|----------|---------|
| 内部带宽 | N/A | 100+ GB/s | - |
| PCIe带宽 | 8-16 GB/s | 8-16 GB/s | - |
| 数据过滤 | Host CPU | Device内部 | 10-100× |
| 向量搜索 | Host GPU | Device FPGA | 5-20× |
| KV attention | GPU | 部分device | 2-10× |

**实测案例**: InstInfer
- 基准: FlexGen (SSD-based推理)
- 提升: 11.1× (13B模型, A6000 GPU)

## 💭 设计考虑

### 何时适合近存储计算？

**✅ 适合**:
```
1. 数据量大 (GB-TB级)
2. 计算可分解 (filter/map/reduce模式)
3. 中间结果小 (< 1% 原始数据)
4. 计算复杂度中等 (不需要高算力)
5. 访问模式可预测
```

**❌ 不适合**:
```
1. 数据量小 (MB级)
2. 需要全局视图
3. 中间结果大
4. 计算极其复杂
5. 随机访问为主
```

### LLM场景的适配度

**KV cache attention**: ⭐⭐⭐⭐
- 数据量大 ✅
- 可分解 (partial attention) ✅
- 结果小 (top-K tokens) ✅
- 计算适中 ✅

**Embedding搜索**: ⭐⭐⭐⭐⭐
- 数据量大 ✅
- 可分解 (向量距离) ✅
- 结果小 (top-K) ✅
- 计算简单 ✅

**模型权重加载**: ⭐⭐
- 数据量大 ✅
- 不可分解 ❌
- 结果大 (完整权重) ❌

## 📚 参考资料

- [[.raw/llm-offloading-research-2026|Offloading技术综述]] - 近存储计算在LLM中的应用
- [[smartssd-programming|SmartSSD编程指南]]
- [[computational-storage-spec|SNIA计算型存储规范]]

## 🔍 产业趋势

### 标准化进展

**SNIA Computational Storage TWG**:
- 定义标准接口
- 推动生态建设
- 互操作性保证

**CXL Consortium**:
- CXL 3.0+ 支持near-memory compute
- 统一内存语义

### 厂商动态

**Samsung**: SmartSSD产品线，支持FPGA编程

**AMD/Xilinx**: SmartSSD开发平台

**NVIDIA**: BlueField DPU集成near-data processing

**Intel**: Optane DC PMM (已停产)

### 开源项目

- **Biscuit** - SmartSSD framework for ML
- **DeepStore** - 深度学习存储加速
- **LeoKV** - KV存储加速

## 💡 未来展望

### 短期 (1-2年)
- LLM KV cache专用near-storage加速器
- 标准化API出现
- 更多SmartSSD产品

### 中期 (3-5年)
- 主流LLM框架原生支持
- CXL + near-storage融合
- 能耗/性能优化成熟

### 长期 (5年+)
- Processing-in-memory (PIM)
- 完全重构的存储计算架构
- AI workload专用存储设备

---

*创建于: 2026-06-04*
*来源: Offloading技术研究综述*
