# 项目范围说明

## 本仓库包含的内容

本仓库**仅包含 PiERN 的数据合成管线**，用于自动生成高质量训练数据。

### ✅ 包含的模块

- **数据生成器**（`data_synthesis/generators/`）
  - MODFLOW 地下水位时序生成器（已实现）
  - 其他任务生成器（待实现）

- **数据增强器**（`data_synthesis/augmenters/`）
  - Identity 扰动
  - Scaling 扰动
  - Offset 扰动

- **质量验证器**（`data_synthesis/validators/`）
  - NaN/Inf 检查
  - 方差检查
  - 物理合理性检查

- **端到端管线**（`data_synthesis/pipeline/`）
  - 流程编排
  - 进度监控
  - 元数据管理

- **工具函数**（`data_synthesis/utils/`）
  - HDF5 读写
  - 数据加载

## 本仓库不包含的内容

### ❌ 不包含的模块

- **PiERN 模型实现**
  - Token Router（令牌级路由器）
  - Text-to-Computation 模块（文本到数值转换）
  - 专家模型（FNO、SoH 神经网络、线性计算器等）
  - LLM 主干网络封装

- **模型训练代码**
  - Stage 1-3 监督学习训练
  - Stage 4 强化学习训练（GRPO/PPO）
  - 训练循环、优化器、损失函数

- **推理代码**
  - 模型推理流程
  - 专家调用逻辑
  - 路由决策

- **评估代码**
  - 性能评估指标
  - 基准测试
  - 可视化工具

## 为什么只包含数据合成？

1. **模块化设计**：数据合成是独立的前置步骤，可以单独开发和测试
2. **复用性**：数据合成管线可以为不同的模型训练方案提供数据
3. **灵活性**：可以在不改动数据合成代码的情况下，迭代模型架构
4. **论文投稿**：数据合成方法是论文的重要贡献点，值得单独开源

## 如何使用生成的数据

数据合成管线生成的 HDF5 文件格式：

```python
# 加载数据
from data_synthesis.utils.hdf5_writer import load_dataset

timeseries, params, param_names = load_dataset("data/modflow/groundwater_timeseries.h5")

# timeseries: [N, n_wells, n_timesteps] - 时序数据
# params: [N, n_params] - 参数矩阵
# param_names: 参数名称列表
```

这些数据可以用于：
- 训练 Text-to-Computation 模块（文本 → 参数映射）
- 训练 Token Router（何时调用专家）
- 微调 LLM 主干网络
- 其他下游任务

## 相关资源

- **论文**：`PiERN.pdf`（ICML 2026 投稿，双盲审稿中）
- **文档**：`docs/data_synthesis_overview.md`（数据合成管线详解）
- **配置**：`configs/data_synthesis/modflow.yaml`（MODFLOW 配置示例）
