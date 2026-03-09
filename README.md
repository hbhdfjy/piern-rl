# PiERN：面向高精度计算与推理融合的令牌级路由网络

PiERN（Physically-isolated Experts Routing Network）的实现代码，投稿至 ICML 2026。

## 概述

PiERN 在单一思维链（CoT）内，通过令牌级动态路由，实现 LLM 语言推理与高精度科学计算专家之间的无缝切换。

本仓库包含两个子项目：

### 子项目1：自动数据合成与增强管线（`data_synthesis/`）

自动构建 PiERN 三阶段监督训练所需的训练数据，无需人工标注：
- 为 Text-to-Computation 训练生成语言模板
- 三种扰动策略：Identity / Scaling / Offset
- 从合成轨迹中自动构造 Token Router 路由标签
- 数据验证与质量过滤

### 子项目2：多轮强化学习（`rl_training/`）

在监督学习 Stage 3 基础上，引入 RL 策略优化：
- 基于 GRPO 对 Router 和 Text2Comp 模块进行训练
- 以多轮专家调用轨迹作为 rollout
- 任务级奖励信号（RMSE、利润、政策对齐）
- KL 约束保护 LLM 语言能力不退化

## 架构

- **物理隔离专家**：预训练的领域专用模型（FNO、SoH 神经网络、线性计算器），训练后永远冻结
- **Text-to-Computation 模块**：Qwen3-0.6B 解码器，将自然语言映射为专家所需数值输入张量
- **Token Router**：轻量级分类器，在每个 token 时间步对 LLM 隐层状态 `h_t` 进行分类，决定继续生成还是调用专家

## 项目结构

```
piern/
├── piern_core/          # 共享基础：专家模型、Router、Text2Comp、LLM 封装
│   ├── models/
│   ├── data/
│   └── utils/
├── data_synthesis/      # 子项目1：自动数据合成与增强
│   ├── pipeline/        # 端到端合成流程编排
│   ├── generators/      # 按任务生成模板与轨迹
│   ├── augmenters/      # 扰动策略（Identity/Scaling/Offset）
│   ├── validators/      # 质量过滤与一致性检查
│   └── utils/
├── rl_training/         # 子项目2：多轮强化学习
│   ├── algorithms/      # GRPO、PPO、REINFORCE 实现
│   ├── reward/          # 按任务实现奖励函数
│   ├── env/             # PiERN rollout 环境（MDP 封装）
│   ├── trainer/         # RL 训练循环
│   └── utils/
├── configs/
│   ├── data_synthesis/
│   └── rl_training/
├── scripts/
│   ├── data_synthesis/
│   └── rl_training/
├── tests/
│   ├── test_data_synthesis/
│   └── test_rl_training/
└── data/
    ├── pdebench/
    ├── gcam/
    └── bms/
```

## 安装

```bash
pip install -r requirements.txt
pip install -e .
```

## 实验任务

| 任务 | 数据路径 | 专家类型 |
|------|----------|----------|
| PDEBench（FNO）| `data/pdebench/` | 神经网络专家（FNO，冻结）|
| GCAM 气候政策 | `data/gcam/` | 9 个领域神经代理 |
| BMS 电池管理系统 | `data/bms/` | SoH 神经网络 + 线性利润公式 |
