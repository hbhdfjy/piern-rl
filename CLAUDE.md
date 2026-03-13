# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作提供指导。

## 项目定位

本仓库**仅包含 PiERN 的数据合成管线**，不包含 PiERN 模型本身的实现（Router、Text2Comp、专家模型等）。

## 当前聚焦

**MODFLOW 地下水模拟任务**：本仓库专注于 MODFLOW 任务的完整三阶段数据生成管线。

当前优先级：
1. ✅ Stage 1：MODFLOW 专家模型数据（已完成 - 14 个场景，6,600 样本）
2. ✅ Stage 2：MODFLOW Text-to-Computation 数据（已完成 - 33,000 训练对）
3. 🎯 Stage 3：MODFLOW Token Router 数据（下一步）

**注**：其他任务（PDEBench、GCAM、BMS）的数据合成已在论文写作阶段完成，不包含在本仓库中。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt
pip install -e .

# Stage 1: 单个场景生成
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/default.yaml

# Stage 1: 批量生成多个场景
python scripts/modflow/batch_generate.py --skip-existing

# Stage 2: 生成 Text-to-Computation 训练数据
python -m piern.text2comp.pipeline \
    --config configs/text2comp/default.yaml

# 检查数据
python scripts/modflow/inspect_data.py data/modflow/baseline_groundwater_timeseries.h5
python scripts/text2comp/inspect_data.py data/text2comp/training_data_llm.jsonl
python scripts/utils/summarize_all.py

# 测试参数空间采样增强
python scripts/modflow/test_augmentation.py
```

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
└── data/                           # 数据目录（.gitignore）
    ├── modflow/
    └── text2comp/
```

## 核心设计

### 1. 模块化架构
- **核心层**（`piern/core/`）：通用工具，所有模拟器共享
- **模拟器层**（`piern/simulators/`）：每个物理模拟器独立隔离
- **任务层**（`piern/text2comp/`, `piern/router/`）：Stage 2/3 数据生成

### 2. 环境隔离
每个物理模拟器有自己的：
- `requirements.txt` - 独立的依赖
- `generator.py` - 数据生成逻辑
- `augmenter.py` - 增强策略
- `pipeline.py` - 完整流程

### 3. Stage 1 数据生成流程

```
参数采样（均匀分布）
    ↓
物理模拟器正演（MODFLOW）
    ↓
质量过滤（NaN、方差、物理范围）
    ↓
参数空间采样增强（V2）
  - 扰动参数 ±5%
  - 运行 MODFLOW 生成新时序
  - 增加 50% 样本数
    ↓
HDF5 存储（gzip 压缩）
```

### 4. Stage 2 数据生成流程

```
加载 Stage 1 数据（所有场景）
    ↓
完全 LLM 生成文本描述
  - 为每个样本生成 N 个不同的文本
  - 零模板依赖，最大化多样性
    ↓
JSONL 存储
```

## 任务支持

本仓库仅支持 **MODFLOW 地下水模拟任务**：

| 任务 | 状态 | 数据路径 | 输入参数 | Stage 1 输出 | Stage 2 输出 |
|------|------|----------|----------|--------------|--------------|
| MODFLOW 地下水位 | ✅ 已完成 | `data/modflow/` | 5 个标量（hk, sy, pumping, strt, rch）| 14 个 HDF5 文件<br>6,600 样本 | training_data_llm.jsonl<br>33,000 训练对 |

## 添加新的物理模拟器

要添加新的物理模拟器（如 OpenFOAM、FEniCS 等）：

1. **创建独立目录**：`piern/simulators/<simulator_name>/`

2. **创建依赖文件**：`requirements.txt`
   ```txt
   # 该模拟器特定的依赖
   some-simulator-package>=1.0.0
   ```

3. **实现生成器**：`generator.py`
   ```python
   def generate_sample(params: dict, cfg: dict) -> np.ndarray:
       """从参数生成单个样本"""
       pass

   def generate_batch(cfg: dict, n_samples: int) -> tuple:
       """批量生成样本"""
       pass
   ```

4. **实现增强器**：`augmenter.py`
   ```python
   def augment_with_parameter_sampling(...):
       """参数空间采样增强"""
       pass
   ```

5. **实现 pipeline**：`pipeline.py`
   ```python
   def run_pipeline(config_path: str):
       """完整的 Stage 1 流程"""
       pass
   ```

6. **创建配置**：`configs/<simulator_name>/default.yaml`

7. **创建脚本**：`scripts/<simulator_name>/generate_stage1.py`

所有新模拟器都遵循相同的接口和流程，确保一致性和可维护性。
