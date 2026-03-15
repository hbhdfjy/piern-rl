# 训练验证快速入门

本文档说明如何使用新实现的训练管线验证 2.5M 数据集的可用性。

---

## 目标

训练一个**轻量级 MLP 模型**，验证数据集可以成功训练并收敛（R² > 0.85）。

---

## 环境准备

### 1. 安装依赖

```bash
# 安装 PyTorch（如果尚未安装）
pip install torch

# 或者安装所有依赖
pip install -r requirements.txt
```

### 2. 验证安装

```bash
# 检查 PyTorch
python -c "import torch; print(f'PyTorch {torch.__version__}')"

# 测试模型
python piern/models/mlp.py

# 测试数据集加载
python piern/training/dataset.py

# 测试评估指标
python piern/training/metrics.py
```

---

## 快速开始

### 单场景训练（baseline）

```bash
# 使用默认配置训练
python scripts/training/train_single_scenario.py

# 预期输出:
# ✅ 训练完成
#    最佳验证 R²: 0.9XXX
#    模型保存至: models/mlp_baseline.pth
```

**预期时间**: 10-30 分钟（取决于 CPU 性能）

**成功标准**: 验证集 R² > 0.85

---

## 训练其他场景

### 训练复杂场景（land_subsidence）

```bash
python scripts/training/train_single_scenario.py \
    --h5-path data/modflow/land_subsidence_timeseries.h5 \
    --config configs/training/mlp_baseline.yaml
```

### 训练多层含水层场景

```bash
python scripts/training/train_single_scenario.py \
    --h5-path data/modflow/multilayer_5layers_timeseries.h5
```

---

## 自定义训练

### 修改训练配置

编辑 `configs/training/mlp_baseline.yaml`:

```yaml
# 增加模型容量
model:
  hidden_dims: [128, 256, 128]  # 默认 [64, 128, 64]

# 调整训练参数
training:
  batch_size: 128               # 默认 256
  learning_rate: 0.0005         # 默认 0.001
  max_epochs: 200               # 默认 100
```

### 使用 GPU 训练

```bash
python scripts/training/train_single_scenario.py --device cuda
```

### 调整批量大小

```bash
python scripts/training/train_single_scenario.py --batch-size 128
```

---

## 评估模型

### 评估已训练的模型

```bash
python scripts/training/evaluate_model.py \
    --model models/mlp_baseline.pth \
    --h5-path data/modflow/baseline_groundwater_timeseries.h5
```

### 可视化预测结果

```bash
# 需要先安装 matplotlib
pip install matplotlib

# 生成可视化
python scripts/training/evaluate_model.py \
    --model models/mlp_baseline.pth \
    --h5-path data/modflow/baseline_groundwater_timeseries.h5 \
    --visualize \
    --n-samples 5
```

**输出**: `models/mlp_baseline_visualization.png`

---

## 文件结构

```
piern/
├── piern/
│   ├── models/                      # 模型定义
│   │   ├── __init__.py
│   │   └── mlp.py                   # 轻量级 MLP
│   │
│   └── training/                    # 训练工具
│       ├── __init__.py
│       ├── dataset.py               # PyTorch Dataset
│       ├── metrics.py               # 评估指标（R²、MSE）
│       └── trainer.py               # 训练循环
│
├── scripts/
│   └── training/                    # 训练脚本
│       ├── train_single_scenario.py # 单场景训练
│       └── evaluate_model.py        # 模型评估
│
├── configs/
│   └── training/                    # 训练配置
│       └── mlp_baseline.yaml
│
└── models/                          # 保存的模型（.gitignore）
    ├── mlp_baseline.pth             # 模型检查点
    └── mlp_baseline.json            # 训练历史
```

---

## 模型架构

### MLP Predictor

```
输入: 5-13 维参数（取决于场景）
  ↓
全连接层 (64 维) + ReLU + Dropout(0.2)
  ↓
全连接层 (128 维) + ReLU + Dropout(0.2)
  ↓
全连接层 (64 维) + ReLU
  ↓
输出层 (1825 维 = 5 wells × 365 timesteps)
```

**参数量**: ~135K

**样本-参数比**: 1000 / 135K = 7.4（充足）

---

## 训练流程

1. **加载数据**: 从 HDF5 文件加载参数和时序数据
2. **数据归一化**: 标准化参数和时序（零均值，单位方差）
3. **划分数据集**: 80% 训练集，20% 验证集
4. **训练循环**:
   - 前向传播：params → model → pred_timeseries
   - 计算损失：MSE(pred, target)
   - 反向传播：更新权重
5. **验证**: 每个 epoch 后评估验证集 R²
6. **早停**: 达到目标 R² 或验证集不再提升时停止
7. **保存模型**: 保存最佳检查点和训练历史

---

## 常见问题

### Q1: 训练太慢怎么办？

**方案1**: 使用 GPU（如果可用）
```bash
python scripts/training/train_single_scenario.py --device cuda
```

**方案2**: 减少批量大小（减少内存占用，但可能更慢）
```bash
python scripts/training/train_single_scenario.py --batch-size 64
```

**方案3**: 减少训练样本（快速验证）
- 手动修改代码，使用 `Subset` 只加载部分数据

---

### Q2: R² 太低怎么办？

**可能原因1**: 数据质量问题
- 检查数据是否有 NaN
- 检查数据范围是否合理

**可能原因2**: 模型容量不足
- 增加隐藏层维度：`[64, 128, 64]` → `[128, 256, 128]`
- 增加隐藏层数量：`[64, 128, 64]` → `[64, 128, 256, 128, 64]`

**可能原因3**: 学习率不当
- 降低学习率：`0.001` → `0.0005`
- 增加训练轮数：`100` → `200`

---

### Q3: 过拟合怎么办？

**症状**: 训练集 R² > 0.99，验证集 R² < 0.70

**解决方案**:
1. 增加 Dropout: `0.2` → `0.3`
2. 增加 L2 正则化: `weight_decay: 0.00001` → `0.0001`
3. 增加训练数据（生成更多样本）
4. 使用数据增强

---

### Q4: 如何批量训练多个场景？

创建一个批量训练脚本:

```bash
#!/bin/bash

scenarios=(
    "baseline_groundwater_timeseries.h5"
    "land_subsidence_timeseries.h5"
    "multilayer_5layers_timeseries.h5"
    "heterogeneous_field_timeseries.h5"
)

for scenario in "${scenarios[@]}"; do
    echo "训练场景: $scenario"
    python scripts/training/train_single_scenario.py \
        --h5-path "data/modflow/$scenario"
done
```

---

## 验证标准

### 最小成功标准（MVP）
- ✅ 单场景（baseline）训练成功
- ✅ 验证集 R² > 0.85
- ✅ 训练时间 < 30 分钟
- ✅ 无 NaN/Inf 错误

### 充分成功标准
- ✅ 3 个复杂场景训练成功
- ✅ 所有场景 R² > 0.80
- ✅ 混合训练 R² > 0.75（可选）

---

## 下一步

训练验证成功后，可以考虑：

1. **实现更复杂的模型**:
   - Fourier Neural Operator (FNO)
   - Transformer（利用时序结构）
   - Physics-Informed Neural Networks (PINN)

2. **扩展到其他模拟器**:
   - SimPEG（地球物理勘探）
   - Devito（地震波传播）
   - TOUGH2（多相流体）

3. **实现 Stage 2**:
   - Text-to-Computation 模块
   - 语言模板生成

4. **实现 Stage 3**:
   - Token Router
   - 多模拟器路由

---

## 参考资料

- **PyTorch 文档**: https://pytorch.org/docs/stable/index.html
- **MLP 教程**: https://pytorch.org/tutorials/beginner/basics/buildmodel_tutorial.html
- **数据加载教程**: https://pytorch.org/tutorials/beginner/basics/data_tutorial.html

---

**最后更新**: 2026-03-15

**作者**: PiERN 项目团队
