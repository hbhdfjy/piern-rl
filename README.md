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
- **参数空间采样增强（V2）**：扰动参数后重新运行物理模拟，保持物理一致性，提高模型精度 2-3 倍
- **质量过滤**：自动过滤低质量样本（NaN、常数序列、物理不合理值）
- **完全 LLM 文本生成**：使用 LLM 为数值参数生成高质量、多样化的文本描述
- **CoT 轨迹合成**：自动构造包含专家调用的推理轨迹（待实现）
- **HDF5/JSONL 存储**：高效存储，支持大规模数据集

## 项目结构

```
piern/
├── piern/                          # 核心包
│   ├── core/                       # 核心共享层
│   │   ├── storage.py              # HDF5/JSONL 读写
│   │   ├── validation.py           # 通用质量过滤
│   │   └── llm_client.py           # LLM 客户端
│   │
│   ├── simulators/                 # 物理模拟器（每个独立隔离）
│   │   └── modflow/                # MODFLOW 地下水模拟
│   │       ├── requirements.txt    # flopy 依赖
│   │       ├── generator.py        # 数据生成
│   │       ├── generator_with_params.py  # 从指定参数生成
│   │       ├── augmenter.py        # 参数空间采样增强
│   │       └── pipeline.py         # Stage 1 pipeline
│   │
│   ├── text2comp/                  # Stage 2: Text-to-Computation
│   │   ├── generator.py            # LLM 文本生成器
│   │   └── pipeline.py             # Stage 2 pipeline
│   │
│   └── router/                     # Stage 3: Token Router（待实现）
│
├── configs/
│   ├── modflow/                    # MODFLOW 配置
│   │   ├── default.yaml
│   │   └── variants/               # 场景变体（14 个）
│   └── text2comp/                  # Text-to-Computation 配置
│       └── default.yaml
│
├── scripts/
│   ├── modflow/                    # MODFLOW 相关脚本
│   │   ├── generate_stage1.py      # Stage 1 数据生成
│   │   ├── test_augmentation.py    # 测试增强
│   │   ├── batch_generate.py       # 批量生成（多场景）
│   │   └── inspect_data.py         # 数据检查
│   ├── text2comp/                  # Text-to-Computation 脚本
│   │   ├── generate_stage2.py      # Stage 2 数据生成
│   │   └── inspect_data.py         # 数据检查
│   └── utils/                      # 通用工具脚本
│       └── summarize_all.py        # 汇总所有数据
│
├── docs/                           # 技术文档
│   ├── architecture.md             # 项目架构详解
│   ├── augmentation_comparison.md  # 数据增强方法对比
│   ├── parameter_augmentation_guide.md  # 参数空间采样增强指南
│   ├── piern_training_data_format.md    # PiERN 训练数据格式
│   └── stage1_data_diversity.md    # Stage 1 数据多样性分析
│
├── research/                       # 调研报告
│   └── 地质时序数据合成工具调研报告.md  # 物理模拟工具调研
│
└── data/                           # 数据目录（.gitignore）
    ├── modflow/                    # MODFLOW 生成的数据
    └── text2comp/                  # Text2Comp 生成的数据
```

## 安装

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速开始

### 1. 生成 Stage 1 数据（专家模型训练数据）

```bash
# 快速测试参数空间采样增强
python scripts/data_synthesis/test_parameter_augmentation.py

# 配置参数
vim configs/data_synthesis/modflow_v2.yaml

# 运行管线（使用参数空间采样增强 V2）
python -m data_synthesis.pipeline.modflow_pipeline_v2 \
    --config configs/data_synthesis/modflow_v2.yaml

# 输出：data/modflow/groundwater_timeseries_v2.h5
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

### 技术文档
- [项目架构详解](docs/architecture.md) - 三层架构设计与模块化说明
- [PiERN 训练数据格式详解](docs/piern_training_data_format.md) - 三阶段数据格式规范
- [数据增强方法对比](docs/augmentation_comparison.md) - V1 vs V2 增强策略分析
- [参数空间采样增强指南](docs/parameter_augmentation_guide.md) - V2 增强详细说明
- [Stage 1 数据多样性分析](docs/stage1_data_diversity.md) - 数据多样性评估

### 调研报告
- [地质时序数据合成工具调研报告](research/地质时序数据合成工具调研报告.md) - 物理模拟器工具调研（2026-03-09）
