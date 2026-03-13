# PiERN 数据合成管线

PiERN（Physically-isolated Experts Routing Network）论文的数据合成代码，投稿至 ICML 2026。

## 概述

本仓库提供自动数据合成与增强管线，为 PiERN **三阶段训练**构建高质量数据集，无需人工标注。

### PiERN 三阶段训练数据

PiERN 需要三种不同格式的训练数据：

1. **Stage 1 数据**（✅ 已实现）：训练专家模型
   - 格式：(数值参数, 时序输出)
   - 示例：`([15.0, 0.12, -200.0, 7.5, 0.0008], [7.5, 7.48, ..., 6.82])`

2. **Stage 2 数据**（✅ 已实现）：训练 Text-to-Computation 模块
   - 格式：(文本描述, 数值参数)
   - 示例：`("水力传导系数 15 m/day，储水系数 0.12，...", [15.0, 0.12, -200.0, 7.5, 0.0008])`
   - 方案：**完全 LLM 生成**（高质量、高多样性）

3. **Stage 3 数据**（🚧 待实现）：训练 Token Router
   - 格式：(CoT 推理轨迹, 路由标签)
   - 示例：包含专家调用位置的完整推理过程

### 核心功能

- **物理模拟驱动**：使用 MODFLOW 等物理模拟器生成真实场景数据
- **三种扰动策略**：Identity / Scaling / Offset，模拟真实场景噪声
- **质量过滤**：自动过滤低质量样本（NaN、常数序列、物理不合理值）
- **语言模板生成**：为数值参数生成多样化的文本描述（待实现）
- **CoT 轨迹合成**：自动构造包含专家调用的推理轨迹（待实现）
- **HDF5/JSONL 存储**：高效存储，支持大规模数据集

## 项目结构

```
piern/
├── data_synthesis/      # 数据合成管线
│   ├── generators/      # Stage 1: 物理模拟数据生成
│   │   └── modflow_generator.py       # ✅ MODFLOW 地下水位
│   ├── text_generators/ # Stage 2: 文本-参数对生成
│   │   ├── llm_client.py              # ✅ LLM 客户端
│   │   └── llm_text_generator.py      # ✅ 完全 LLM 生成
│   ├── trajectory_generators/         # Stage 3: CoT 轨迹生成（待实现）
│   │   ├── cot_generator.py           # 🚧 推理轨迹合成
│   │   └── route_labeler.py           # 🚧 路由标签标注
│   ├── augmenters/      # 扰动增强（Identity/Scaling/Offset）
│   ├── validators/      # 质量过滤
│   ├── pipeline/        # 端到端流程编排
│   │   ├── modflow_pipeline.py        # ✅ Stage 1 管线
│   │   ├── text2comp_pipeline_llm.py  # ✅ Stage 2 完全 LLM 管线
│   │   └── router_pipeline.py         # 🚧 Stage 3 管线（待实现）
│   └── utils/           # 工具函数
├── configs/
│   └── data_synthesis/  # 配置文件（YAML）
├── scripts/
│   └── data_synthesis/  # 运行脚本
├── tests/
│   └── test_data_synthesis/  # 单元测试
├── docs/
│   ├── data_synthesis_overview.md        # 数据合成管线详解
│   └── piern_training_data_format.md     # PiERN 训练数据格式详解
└── data/                # 输出数据目录
    └── modflow/
        ├── groundwater_timeseries.h5     # ✅ Stage 1 数据
        ├── text2comp_training.jsonl      # 🚧 Stage 2 数据
        └── router_training.jsonl         # 🚧 Stage 3 数据
```

## 安装

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速开始

### 1. 生成 Stage 1 数据（专家模型训练数据）

```bash
# 配置参数
vim configs/data_synthesis/modflow.yaml

# 运行管线
python -m data_synthesis.pipeline.modflow_pipeline \
    --config configs/data_synthesis/modflow.yaml

# 输出：data/modflow/groundwater_timeseries.h5
```

### 2. 加载 Stage 1 数据

```python
from data_synthesis.utils.hdf5_writer import load_dataset

timeseries, params, param_names = load_dataset(
    "data/modflow/groundwater_timeseries.h5"
)
print(f"时序形状: {timeseries.shape}")  # [N, 5, 365]
print(f"参数形状: {params.shape}")      # [N, 5]

# 用于训练专家模型
# expert_model.fit(params, timeseries)
```

### 3. 生成 Stage 2 数据（✅ 已实现 - 完全 LLM 方案）

```bash
# 1. 快速测试 API
python scripts/data_synthesis/quick_test_api.py

# 2. Dry-run（仅 10 个样本）
python scripts/data_synthesis/run_text2comp_llm.py --dry-run

# 3. 运行完整管线
python scripts/data_synthesis/run_text2comp_llm.py

# 输出：33,000 训练对，耗时 ~30-60 分钟，成本 ~$0.75
```

**特点**：
- ✅ 完全 LLM 生成，零模板依赖
- ✅ 极高的语言多样性和自然度
- ✅ 自动验证参数值准确性
- ✅ 支持多种 LLM 提供商（OpenAI、Anthropic、SiliconFlow）

**详细文档**: [完全 LLM 生成快速开始](docs/QUICK_START_LLM.md)

### 4. 生成 Stage 3 数据（待实现）

```bash
# 从 Stage 1 + Stage 2 数据生成 CoT 轨迹
python -m data_synthesis.pipeline.router_pipeline \
    --input data/modflow/groundwater_timeseries.h5 \
    --output data/modflow/router_training.jsonl

# 输出格式：
# {"question": "...", "cot_trajectory": [...], "expert_calls": [...]}
```

## MODFLOW 任务三阶段数据生成

**本仓库专注于 MODFLOW 地下水模拟任务**。其他任务（PDEBench、GCAM、BMS）的数据合成已在论文写作阶段完成。

| 阶段 | 目标 | 状态 | 输出格式 |
|------|------|------|----------|
| Stage 1 | 专家模型训练数据 | ✅ 已完成 | HDF5: 14 个场景，6,600 样本 |
| Stage 2 | Text-to-Computation 数据 | ✅ 已完成 | JSONL: 33,000 训练对 |
| Stage 3 | Token Router 数据 | 🎯 下一步 | JSONL: (question, cot, routes) |

## 文档

- [数据合成管线详解](docs/data_synthesis_overview.md) - 完整的设计文档和使用指南
- [PiERN 训练数据格式详解](docs/piern_training_data_format.md) - 三阶段数据格式规范
- [项目路线图](ROADMAP.md) - ⭐ **MODFLOW 三阶段攻关计划**
