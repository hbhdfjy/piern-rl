# PiERN 数据合成管线详解

## 概述

PiERN 数据合成管线自动构建高质量训练数据，无需人工标注。当前实现基于 MODFLOW 地下水位时序预测任务。

**注意**：本仓库仅包含数据合成管线，不包含 PiERN 模型本身的实现。

## 核心设计理念

### 1. 物理模拟驱动的数据生成
- 使用 flopy/MODFLOW 进行地下水位正演模拟
- 参数空间采样：水力传导系数 K、储水系数、抽水量、初始水头、补给量
- 输出：多观测井的水头时序数据

### 2. 三种扰动增强策略

#### Identity 扰动
- **定义**：x' = x（原样保留）
- **目的**：保持原始样本在增强数据集中的比例
- **比例**：40%

#### Scaling 扰动
- **定义**：x' = x · k，k ∈ [0.8, 1.2]
- **物理含义**：模拟含水层整体水位抬升/下降
- **比例**：30%

#### Offset 扰动
- **定义**：x' = x + b，b ~ N(0, 0.1·std(x))
- **物理含义**：模拟观测井传感器零漂、测量误差
- **比例**：30%

### 3. 质量过滤机制

对生成的时序数据进行三层过滤：

1. **NaN/Inf 检查**：丢弃 NaN 比例 > 5% 的样本
2. **方差检查**：丢弃方差 < 1e-6 的常数序列（模型未收敛）
3. **物理合理性**：丢弃水头值超出 [-5, 15] 米的样本（模型发散）

## 数据流程

```
参数采样（均匀分布）
    ↓
MODFLOW 正演模拟
    ↓
质量过滤（NaN、方差、物理范围）
    ↓
扰动增强（Identity/Scaling/Offset）
    ↓
HDF5 存储（压缩格式）
```

## 输入输出格式

### 输入参数（标量，第一梯队）
```python
params = {
    "hk": 1.0~50.0,        # 水力传导系数 K（m/day）
    "sy": 0.05~0.30,       # 储水系数（无量纲）
    "pumping": -500~-50,   # 抽水量 Q（m³/day）
    "strt": 5.0~9.0,       # 初始水头（m）
    "rch": 0.0001~0.002,   # 补给量（m/day）
}
```

### 输出时序
```python
timeseries.shape = [N, n_wells, n_timesteps]
# 示例：[1000, 5, 365]
# 1000 个样本，5 个观测井，365 天时序
```

### HDF5 数据集结构
```
groundwater_timeseries.h5
├── timeseries [N, 5, 365]   # 水头时序（float32，gzip 压缩）
├── params [N, 5]             # 参数矩阵（float32，gzip 压缩）
├── param_names [5]           # 参数名称（["hk", "sy", "pumping", "strt", "rch"]）
└── metadata/
    ├── n_original            # 原始样本数
    ├── n_augmented           # 增强后样本数
    ├── augmentation_counts   # 各扰动类型数量
    └── config_path           # 配置文件路径
```

## 代码组织

### `generators/modflow_generator.py`
- **职责**：参数采样 + MODFLOW 正演
- **核心函数**：
  - `generate_sample()` — 生成单个样本
  - `generate_batch()` — 批量生成 N 个样本
  - `_run_modflow()` — 构建并运行 MODFLOW 模型

### `augmenters/perturbation.py`
- **职责**：实现三种扰动策略
- **核心函数**：
  - `apply_identity()` — Identity 扰动
  - `apply_scaling()` — Scaling 扰动
  - `apply_offset()` — Offset 扰动
  - `augment_dataset()` — 批量增强整个数据集

### `validators/quality_filter.py`
- **职责**：质量过滤与异常检测
- **核心函数**：
  - `filter_sample()` — 单样本质量检查
  - `filter_dataset()` — 批量过滤数据集

### `pipeline/modflow_pipeline.py`
- **职责**：端到端流程编排
- **核心函数**：
  - `run_pipeline()` — 执行完整管线（生成→过滤→增强→存储）

### `utils/hdf5_writer.py`
- **职责**：HDF5 读写工具
- **核心函数**：
  - `save_dataset()` — 保存数据集
  - `load_dataset()` — 加载数据集

## 使用方法

### 1. 配置文件
编辑 `configs/data_synthesis/modflow.yaml`：
```yaml
n_samples: 1000          # 生成样本总数
n_timesteps: 365         # 时间步数（天）
n_wells: 5               # 观测井数量

params:
  hk_min: 1.0
  hk_max: 50.0
  # ... 其他参数范围

augmentation:
  identity_ratio: 0.4
  scaling_ratio: 0.3
  # ... 扰动配置

validation:
  max_nan_ratio: 0.05
  min_variance: 1e-6
  # ... 过滤阈值
```

### 2. 运行管线
```bash
python -m data_synthesis.pipeline.modflow_pipeline \
    --config configs/data_synthesis/modflow.yaml
```

### 3. 加载数据
```python
from data_synthesis.utils.hdf5_writer import load_dataset

timeseries, params, param_names = load_dataset(
    "data/modflow/groundwater_timeseries.h5"
)
print(f"时序形状: {timeseries.shape}")
print(f"参数形状: {params.shape}")
print(f"参数名称: {param_names}")
```

## 关键设计决策

### 为什么用 MODFLOW？
- 成熟的地下水模拟工具，物理机制清晰
- 参数空间简单（5 个标量），适合第一梯队验证
- 输出时序数据，适合测试 Text2Comp 模块

### 为什么需要扰动增强？
- 单纯参数采样数据多样性不足
- 扰动策略模拟真实场景的系统偏差（传感器漂移、区域水位变化）
- 提升模型泛化能力

### 为什么质量过滤必不可少？
- MODFLOW 求解器可能不收敛（参数组合不合理）
- 网格边界条件可能导致数值发散
- 过滤确保训练数据的物理合理性

## 架构设计原则

当前管线专注于 MODFLOW 任务，架构采用模块化设计：

- **生成器**：负责从物理模拟器/专家模型获取原始数据
- **增强器**：任务无关，可跨任务复用
- **验证器**：任务特定，根据物理约束定制
- **管线**：串联上述三个模块，提供统一接口

**注**：其他任务（PDEBench、GCAM、BMS）的数据合成已在论文写作阶段完成。

## 性能考虑

### 计算瓶颈
- MODFLOW 正演是主要耗时环节（单样本 ~1-5 秒）
- 建议使用多进程并行（未来优化方向）

### 存储优化
- HDF5 gzip 压缩（压缩率约 4:1）
- float32 精度足够，避免 float64 浪费

### 失败重试
- 允许最多 3 倍失败重试（`max_attempts = n_samples * 3`）
- 若失败率过高，检查 MODFLOW 可执行文件是否在 PATH 中

## 下一步工作

1. **Stage 3 数据生成**：实现 Token Router 训练数据生成
2. **并行加速**：多进程并行运行 MODFLOW
3. **数据增强优化**：探索更多扰动策略（如时间平移、频域扰动）
4. **质量分析工具**：可视化生成数据的统计分布
