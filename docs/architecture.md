# PiERN 数据合成管线架构

## 🎯 设计理念

### 核心原则

1. **模块化**：清晰的三层架构（核心-模拟器-任务）
2. **隔离性**：每个物理模拟器独立，依赖不冲突
3. **可扩展**：添加新模拟器只需复制模板
4. **易理解**：目录结构直观，功能职责明确

### 设计目标

- ✅ 支持多个物理模拟器（MODFLOW、OpenFOAM、FEniCS 等）
- ✅ 每个模拟器环境隔离，避免依赖冲突
- ✅ 通用功能共享，避免代码重复
- ✅ 新增模拟器时，不影响现有代码

---

## 📐 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                        任务层                                 │
│  piern/text2comp/  piern/router/                            │
│  (Stage 2 数据)    (Stage 3 数据)                            │
└─────────────────────────────────────────────────────────────┘
                            ↑
                            │ 使用
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      模拟器层                                 │
│  piern/simulators/modflow/                                  │
│  piern/simulators/openfoam/    (未来)                       │
│  piern/simulators/fenics/      (未来)                       │
│  (Stage 1 数据生成，每个独立隔离)                             │
└─────────────────────────────────────────────────────────────┘
                            ↑
                            │ 使用
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       核心层                                  │
│  piern/core/storage.py      (HDF5/JSONL 读写)               │
│  piern/core/validation.py   (通用质量过滤)                   │
│  piern/core/llm_client.py   (LLM 客户端)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 核心层（piern/core/）

### 职责
提供所有模拟器和任务共享的通用功能。

### 模块

#### `storage.py`
- **功能**：HDF5 和 JSONL 文件的读写
- **API**：
  ```python
  save_dataset(output_path, timeseries, params, param_names, metadata)
  load_dataset(file_path) -> (timeseries, params, param_names)
  ```

#### `validation.py`
- **功能**：通用质量过滤
- **检查项**：
  - NaN/Inf 比例
  - 方差阈值（过滤常数序列）
  - 物理合理性（值范围）
- **API**：
  ```python
  filter_sample(timeseries, cfg) -> bool
  filter_dataset(timeseries, params, cfg) -> (filtered_ts, filtered_params, mask)
  ```

#### `llm_client.py`
- **功能**：统一的 LLM API 客户端
- **支持**：
  - OpenAI (gpt-3.5-turbo, gpt-4)
  - SiliconFlow (Qwen2.5-7B, GLM-5)
  - 自定义 API
- **API**：
  ```python
  client = LLMClient(provider, model, api_key, base_url)
  response = client.generate(prompt, temperature, max_tokens)
  ```

---

## 🔬 模拟器层（piern/simulators/）

### 职责
每个物理模拟器独立实现 Stage 1 数据生成。

### 环境隔离
每个模拟器有自己的：
- `requirements.txt` - 独立的依赖
- `generator.py` - 数据生成逻辑
- `augmenter.py` - 参数空间采样增强
- `pipeline.py` - 完整的 Stage 1 流程

### MODFLOW 示例（piern/simulators/modflow/）

#### 文件结构
```
modflow/
├── __init__.py
├── requirements.txt        # flopy>=3.3.5
├── generator.py            # MODFLOW 正演模拟
├── generator_with_params.py  # 从指定参数生成
├── augmenter.py            # 参数空间采样增强
└── pipeline.py             # Stage 1 完整流程
```

#### 数据生成流程
```
参数采样（均匀分布）
    ↓
MODFLOW 正演模拟（generate_batch）
    ↓
质量过滤（filter_dataset）
    ↓
参数空间采样增强
  ├─ 扰动参数 ±5%
  ├─ 运行 MODFLOW 生成新时序
  └─ 合并原始样本和新样本
    ↓
HDF5 存储（save_dataset）
```

#### 关键 API
```python
# 随机参数生成
generate_sample(cfg) -> (timeseries, params)
generate_batch(cfg, n_samples) -> (timeseries, params, param_names)

# 从指定参数生成
generate_sample_from_params(params_dict, cfg) -> timeseries
generate_batch_from_params(params_array, param_names, cfg) -> (timeseries, params)

# 参数空间采样增强
perturb_params(params, perturbation_ratio) -> perturbed_params
augment_with_parameter_sampling(timeseries, params, param_names, aug_cfg, modflow_cfg)

# 完整流程
run_pipeline(config_path) -> output_file
```

---

## 📝 任务层

### Stage 2: Text-to-Computation（piern/text2comp/）

#### 职责
为 Stage 1 数据生成文本描述，构建 Text-to-Computation 训练数据。

#### 文件结构
```
text2comp/
├── __init__.py
├── generator.py            # LLM 文本生成器
└── pipeline.py             # Stage 2 完整流程
```

#### 数据生成流程
```
加载 Stage 1 数据（所有场景）
    ↓
完全 LLM 生成文本描述
  - 为每个样本生成 N 个不同的文本
  - 零模板依赖，最大化多样性
    ↓
JSONL 存储
```

#### 关键 API
```python
# LLM 文本生成器
generator = LLMTextGenerator(llm_client, temperature, max_tokens, style_diversity)
texts = generator.generate_multiple(params_dict, n_variants, scenario)

# 完整流程
run_llm_pipeline(config_path) -> output_file
```

### Stage 3: Token Router（piern/router/）

**状态**：待实现

**职责**：生成包含专家调用的 CoT 推理轨迹，训练 Token Router。

---

## 🗂️ 配置文件组织

### 结构
```
configs/
├── modflow/                    # MODFLOW 配置
│   ├── default.yaml            # 默认配置
│   └── variants/               # 场景变体
│       ├── baseline.yaml       # 基线场景
│       ├── high_permeability.yaml
│       ├── low_permeability.yaml
│       ├── heavy_pumping.yaml
│       ├── light_pumping.yaml
│       ├── arid_region.yaml
│       ├── humid_region.yaml
│       ├── urban_water_supply.yaml
│       ├── artificial_recharge.yaml
│       ├── short_term_daily.yaml
│       ├── medium_term_halfyear.yaml
│       ├── long_term_twoyears.yaml
│       ├── coarse_grid_10x10.yaml
│       └── fine_grid_40x40.yaml
│
├── text2comp/                  # Text-to-Computation 配置
│   └── default.yaml
│
└── [future_simulator]/         # 其他模拟器配置
```

### 配置文件格式（YAML）

#### MODFLOW 配置示例
```yaml
# 输出路径
output_dir: data/modflow
output_file: groundwater_timeseries.h5

# 合成规模
n_samples: 1000
n_timesteps: 365
n_wells: 5

# 模型网格
grid:
  nrow: 20
  ncol: 20
  nlay: 1
  delr: 100.0
  delc: 100.0
  top: 10.0
  botm: 0.0

# 参数采样范围
params:
  hk_min: 1.0
  hk_max: 50.0
  sy_min: 0.05
  sy_max: 0.30
  pumping_min: -500.0
  pumping_max: -50.0
  strt_min: 5.0
  strt_max: 9.0
  rch_min: 0.0001
  rch_max: 0.002

# 参数空间采样增强
augmentation:
  enabled: true
  method: "parameter_sampling"
  n_augmented_per_sample: 0.5    # 增加 50%
  perturbation_ratio: 0.05       # 参数扰动 ±5%

# 质量过滤
validation:
  max_nan_ratio: 0.05
  min_variance: 0.000001
  max_head_value: 15.0
  min_head_value: -5.0

# 随机种子
seed: 42
```

---

## 📜 脚本组织

### 结构
```
scripts/
├── modflow/                    # MODFLOW 相关脚本
│   ├── generate_stage1.py      # Stage 1 数据生成入口
│   ├── test_augmentation.py    # 测试参数空间采样增强
│   ├── batch_generate.py       # 批量生成（多场景）
│   ├── generate_configs.py     # 生成配置文件
│   └── inspect_data.py         # 数据检查
│
├── text2comp/                  # Text-to-Computation 脚本
│   ├── generate_stage2.py      # Stage 2 数据生成入口
│   └── inspect_data.py         # 数据检查
│
└── utils/                      # 通用工具脚本
    └── summarize_all.py        # 汇总所有数据
```

### 使用方式

#### 单个场景生成
```bash
python scripts/modflow/generate_stage1.py \
    --config configs/modflow/default.yaml
```

#### 批量生成多个场景
```bash
python scripts/modflow/batch_generate.py \
    --config-dir configs/modflow/variants \
    --skip-existing
```

#### 生成 Text-to-Computation 数据
```bash
python scripts/text2comp/generate_stage2.py \
    --config configs/text2comp/default.yaml
```

---

## 🔌 添加新的物理模拟器

### 步骤

#### 1. 创建模拟器目录
```bash
mkdir -p piern/simulators/<simulator_name>
```

#### 2. 创建依赖文件
```bash
cat > piern/simulators/<simulator_name>/requirements.txt << EOF
# 该模拟器特定的依赖
some-simulator-package>=1.0.0
EOF
```

#### 3. 实现生成器（generator.py）
```python
"""
<Simulator Name> 数据生成器。
"""

import numpy as np
from typing import Dict, Any


def generate_sample(cfg: Dict[str, Any]) -> tuple:
    """
    生成单个样本。

    Args:
        cfg: 配置字典

    Returns:
        (timeseries, params) 元组
    """
    # TODO: 实现参数采样
    params = sample_params(cfg)

    # TODO: 运行物理模拟器
    timeseries = run_simulator(params, cfg)

    return timeseries, params


def generate_batch(
    cfg: Dict[str, Any],
    n_samples: int,
    seed: int = 42
) -> tuple:
    """
    批量生成样本。

    Args:
        cfg: 配置字典
        n_samples: 样本数量
        seed: 随机种子

    Returns:
        (timeseries, params, param_names) 元组
    """
    # TODO: 实现批量生成
    pass
```

#### 4. 实现增强器（augmenter.py）
```python
"""
<Simulator Name> 参数空间采样增强。
"""

import numpy as np
from piern.simulators.<simulator_name>.generator_with_params import generate_batch_from_params


def perturb_params(
    params: np.ndarray,
    param_names: list,
    perturbation_ratio: float = 0.05,
    rng: np.random.Generator = None
) -> np.ndarray:
    """扰动参数。"""
    if rng is None:
        rng = np.random.default_rng()

    N, n_params = params.shape
    delta = rng.uniform(-perturbation_ratio, perturbation_ratio, size=(N, n_params))
    perturbed_params = params * (1.0 + delta)

    return perturbed_params.astype(np.float32)


def augment_with_parameter_sampling(...):
    """参数空间采样增强。"""
    # TODO: 实现增强逻辑
    pass
```

#### 5. 实现 pipeline（pipeline.py）
```python
"""
<Simulator Name> Stage 1 数据生成管线。
"""

import argparse
import yaml
from piern.simulators.<simulator_name>.generator import generate_batch
from piern.core.validation import filter_dataset
from piern.core.storage import save_dataset


def run_pipeline(config_path: str) -> str:
    """运行完整的 Stage 1 流程。"""
    # TODO: 实现完整流程
    pass


def main():
    parser = argparse.ArgumentParser(
        description="<Simulator Name> Stage 1 数据生成"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/<simulator_name>/default.yaml",
        help="配置文件路径",
    )
    args = parser.parse_args()

    run_pipeline(args.config)


if __name__ == "__main__":
    main()
```

#### 6. 创建配置文件
```bash
mkdir -p configs/<simulator_name>
cat > configs/<simulator_name>/default.yaml << EOF
# <Simulator Name> 配置
output_dir: data/<simulator_name>
output_file: <simulator_name>_data.h5

# TODO: 添加配置项
EOF
```

#### 7. 创建脚本
```bash
mkdir -p scripts/<simulator_name>
cat > scripts/<simulator_name>/generate_stage1.py << EOF
#!/usr/bin/env python3
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from piern.simulators.<simulator_name>.pipeline import main

if __name__ == "__main__":
    main()
EOF

chmod +x scripts/<simulator_name>/generate_stage1.py
```

#### 8. 更新 setup.py
```python
entry_points={
    "console_scripts": [
        "piern-modflow=piern.simulators.modflow.pipeline:main",
        "piern-<simulator_name>=piern.simulators.<simulator_name>.pipeline:main",  # 新增
        "piern-text2comp=piern.text2comp.pipeline:main",
    ],
},
```

---

## 📊 数据流

### Stage 1: 专家模型数据
```
参数采样 → 物理模拟 → 质量过滤 → 参数空间增强 → HDF5 存储
```

### Stage 2: Text-to-Computation 数据
```
加载 Stage 1 数据 → LLM 生成文本 → JSONL 存储
```

### Stage 3: Token Router 数据（待实现）
```
加载 Stage 1/2 数据 → 生成 CoT 轨迹 → 标注路由标签 → JSONL 存储
```

---

## 🎯 设计优势

### 1. 模块化
- 清晰的三层架构
- 每层职责明确
- 层与层之间通过定义良好的接口交互

### 2. 隔离性
- 每个物理模拟器独立
- 依赖不冲突
- 修改一个模拟器不影响其他

### 3. 可扩展性
- 添加新模拟器：复制模板，实现接口
- 添加新任务：在任务层新增目录
- 添加新功能：在核心层扩展

### 4. 易维护性
- 相关代码聚合在一起
- 目录结构直观
- 文档完善

### 5. 易测试性
- 每个模块可独立测试
- 核心层、模拟器层、任务层分别测试
- 集成测试覆盖完整流程

---

## 📚 相关文档

- [CLAUDE.md](../CLAUDE.md) - Claude Code 工作指南
- [README.md](../README.md) - 项目主文档
- [modflow_guide.md](modflow_guide.md) - MODFLOW 使用指南（待创建）
- [text2comp_guide.md](text2comp_guide.md) - Text-to-Computation 指南（待创建）
- [adding_new_simulator.md](adding_new_simulator.md) - 添加新模拟器详细指南（待创建）
