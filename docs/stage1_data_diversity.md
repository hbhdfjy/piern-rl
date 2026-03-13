# Stage 1 数据多样化设计

## 🎯 目标

为 PiERN 专家模型生成**多样化、高质量**的 MODFLOW 训练数据，覆盖不同的：
- 地质条件（高/中/低渗透）
- 时空尺度（短期/中期/长期，粗/细网格）
- 水文场景（强/弱抽水，干旱/湿润区）

## 📊 数据多样化策略

### 1. 地质条件变体（3 类）

模拟不同岩性的含水层特征：

| 类型 | 岩性 | hk 范围 (m/day) | sy 范围 | 样本数 |
|------|------|----------------|---------|--------|
| 高渗透 | 砾石、粗砂 | 20 - 100 | 0.20 - 0.35 | 500 |
| 中等渗透 | 细砂、中砂 | 5 - 25 | 0.10 - 0.25 | 500 |
| 低渗透 | 粉砂、粘土 | 0.1 - 5 | 0.01 - 0.10 | 500 |

**物理意义**：
- **高渗透**：水流快，水位响应迅速，适合大规模开采
- **低渗透**：水流慢，水位响应缓慢，易过度开采
- **中等渗透**：最常见的含水层类型

### 2. 时空尺度变体（5 类）

覆盖不同的模拟时长和空间分辨率：

| 类型 | 时间步 | 网格 | 观测井 | 应用场景 | 样本数 |
|------|--------|------|--------|----------|--------|
| 短期日尺度 | 30 天 | 20×20 | 3 | 抽水试验、应急响应 | 500 |
| 中期半年 | 180 天 | 20×20 | 5 | 季节性预测 | 500 |
| 长期两年 | 730 天 | 20×20 | 7 | 长期规划、气候影响 | 300 |
| 细网格 | 365 天 | 40×40 | 9 | 局部精细模拟 | 300 |
| 粗网格 | 365 天 | 10×10 | 3 | 区域尺度评估 | 500 |

**设计考虑**：
- **短期**：捕捉快速响应过程
- **长期**：捕捉趋势和季节变化
- **细网格**：空间异质性，计算量大
- **粗网格**：区域特征，计算效率高

### 3. 抽水强度变体（3 类）

模拟不同的地下水开采强度：

| 类型 | pumping 范围 (m³/day) | rch 范围 (m/day) | 场景 | 样本数 |
|------|----------------------|-----------------|------|--------|
| 强抽水 | -1000 ~ -500 | 0.0001 - 0.001 | 过度开采、水位下降 | 500 |
| 弱抽水 | -100 ~ -20 | 0.0005 - 0.003 | 合理开采、可持续 | 500 |
| 人工补给 | +50 ~ +500 | 0.0001 - 0.001 | 注水回灌、修复 | 300 |

**物理意义**：
- **强抽水**：水位持续下降，形成大范围降落漏斗
- **弱抽水**：水位稳定或缓慢下降
- **人工补给**：水位上升，地下水库补充

### 4. 混合场景（3 类）

组合不同条件，模拟真实世界复杂性：

| 场景 | 特征 | hk | pumping | rch | 样本数 |
|------|------|----|---------|----|--------|
| 干旱区 | 低补给 + 中等抽水 | 3-20 | -300~-100 | 0.00001-0.0003 | 400 |
| 湿润区 | 高补给 + 弱抽水 | 10-50 | -200~-50 | 0.002-0.008 | 400 |
| 城市供水 | 中高渗透 + 强抽水 + 短期 | 15-40 | -800~-300 | 0.0003-0.002 | 400 |

**实际应用**：
- **干旱区**：西北地区，水资源紧张
- **湿润区**：南方地区，水量丰富
- **城市供水**：城市水源地，短期调度

## 📈 数据统计

### 总体规模

```
总配置数: 15
总样本数: 7,100
  = 基准配置 1,000
  + 地质变体 1,500
  + 时空变体 2,100
  + 抽水变体 1,300
  + 混合场景 1,200
```

### 参数覆盖范围

| 参数 | 全局最小值 | 全局最大值 | 跨度 |
|------|-----------|-----------|------|
| hk | 0.1 m/day | 100 m/day | 1000× |
| sy | 0.01 | 0.35 | 35× |
| pumping | -1000 m³/day | +500 m³/day | 跨零点 |
| strt | 5.0 m | 9.0 m | - |
| rch | 0.00001 m/day | 0.008 m/day | 800× |

### 时空覆盖范围

| 维度 | 最小值 | 最大值 | 变化范围 |
|------|--------|--------|----------|
| 时间步 | 30 天 | 730 天 | 24× |
| 网格 | 10×10 | 40×40 | 16× |
| 观测井 | 3 个 | 9 个 | 3× |

## 🔧 自动化生成流程

```
1. 配置生成
   python scripts/data_synthesis/generate_modflow_configs.py
   → 生成 15 个 YAML 配置文件

2. 批量运行
   python scripts/data_synthesis/batch_generate_modflow.py
   → 运行所有配置，生成 HDF5 数据

3. 数据检查
   python scripts/data_synthesis/inspect_stage1_data.py
   → 验证数据质量
```

### 批量运行选项

```bash
# 串行运行（安全，便于调试）
python scripts/data_synthesis/batch_generate_modflow.py

# 并行运行（快速，利用多核）
python scripts/data_synthesis/batch_generate_modflow.py --parallel --max-workers 4

# 跳过已生成的文件（断点续传）
python scripts/data_synthesis/batch_generate_modflow.py --skip-existing

# 运行单个配置（测试）
python scripts/data_synthesis/batch_generate_modflow.py --single baseline.yaml
```

## 📁 输出文件结构

```
data/modflow/
├── baseline_groundwater_timeseries.h5              # 1,000 样本
├── high_permeability_groundwater_timeseries.h5     # 500 样本
├── low_permeability_groundwater_timeseries.h5      # 500 样本
├── medium_permeability_groundwater_timeseries.h5   # 500 样本
├── short_term_daily_groundwater_timeseries.h5      # 500 样本
├── medium_term_halfyear_groundwater_timeseries.h5  # 500 样本
├── long_term_twoyears_groundwater_timeseries.h5    # 300 样本
├── fine_grid_40x40_groundwater_timeseries.h5       # 300 样本
├── coarse_grid_10x10_groundwater_timeseries.h5     # 500 样本
├── heavy_pumping_groundwater_timeseries.h5         # 500 样本
├── light_pumping_groundwater_timeseries.h5         # 500 样本
├── artificial_recharge_groundwater_timeseries.h5   # 300 样本
├── arid_region_groundwater_timeseries.h5           # 400 样本
├── humid_region_groundwater_timeseries.h5          # 400 样本
└── urban_water_supply_groundwater_timeseries.h5    # 400 样本
```

每个 HDF5 文件包含：
- `timeseries`: [N, n_wells, n_timesteps] 水头时序
- `params`: [N, 5] 输入参数
- `param_names`: ['hk', 'sy', 'pumping', 'strt', 'rch']
- `metadata/`: 增强类型、配置信息等

## 🎯 数据用途

这些多样化数据将用于训练 PiERN 的**专家模型**：

```python
# 训练目标
输入: params [batch, 5]           # 物理参数
输出: timeseries [batch, n_wells, n_timesteps]  # 水头预测

# 模型需要学习：
1. 不同地质条件下的水流规律
2. 不同时空尺度的动态响应
3. 不同开采强度的影响模式
4. 复杂场景的综合效应
```

**优势**：
- **泛化能力强**：覆盖广泛的参数空间
- **鲁棒性高**：适应不同的应用场景
- **物理合理**：基于真实的 MODFLOW 模拟
- **可扩展**：易于添加新的配置变体

## 🔄 后续扩展

### 可添加的变体

1. **多层含水层**：nlay > 1，模拟承压-非承压系统
2. **多井场景**：多个抽水井，井间干扰
3. **非均质性**：空间变化的 hk、sy
4. **瞬态边界**：时变的边界条件、补给
5. **季节性**：周期性的抽水、补给模式

### 质量控制

- 自动过滤不收敛的模拟
- 检查物理合理性
- 统计参数分布
- 可视化时序特征

## 📝 配置文件示例

```yaml
# 高渗透含水层配置
description: 高渗透含水层（砾石、粗砂）
output_dir: data/modflow
output_file: high_permeability_groundwater_timeseries.h5
n_samples: 500
n_timesteps: 365
n_wells: 5

grid:
  nrow: 20
  ncol: 20
  nlay: 1
  delr: 100.0
  delc: 100.0
  top: 10.0
  botm: 0.0

params:
  hk_min: 20.0    # 高渗透
  hk_max: 100.0
  sy_min: 0.20    # 高给水度
  sy_max: 0.35
  pumping_min: -800.0  # 可承受强抽水
  pumping_max: -200.0
  strt_min: 5.0
  strt_max: 9.0
  rch_min: 0.001   # 补给快
  rch_max: 0.005

validation:
  max_nan_ratio: 0.05
  min_variance: 0.000001
  max_head_value: 20.0
  min_head_value: -10.0

seed: 1234
```

## 🚀 预计性能

**单个配置运行时间**（基于 baseline 测试）：
- 500 样本 × 365 天：~35 秒
- 1000 样本 × 365 天：~73 秒
- 300 样本 × 730 天：~65 秒

**总耗时估算**（串行）：
- 15 个配置：~15 分钟

**并行加速**（4 核）：
- 预计：~5 分钟

---

**生成日期**: 2026-03-13
**版本**: 1.0
