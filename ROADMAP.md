# 项目路线图

## 当前聚焦：MODFLOW 任务完整三阶段数据生成

**核心目标**：完成 MODFLOW 任务的 Stage 1/2/3 数据生成，形成完整的数据合成管线。

**注**：其他任务（PDEBench、GCAM、BMS）的数据合成已在论文写作阶段完成，不包含在本仓库中。

---

## 阶段 1：MODFLOW Stage 1 数据生成 ✅

**目标**：生成专家模型训练数据

**状态**：✅ 已完成

**输出**：
```
data/modflow/groundwater_timeseries.h5
├── timeseries: [N, 5, 365]  # 水头时序
├── params: [N, 5]            # 输入参数
└── param_names: ["hk", "sy", "pumping", "strt", "rch"]
```

**已实现功能**：
- ✅ 参数采样（5 个标量）
- ✅ MODFLOW 正演模拟（flopy）
- ✅ 质量过滤（NaN、方差、物理范围）
- ✅ 扰动增强（Identity/Scaling/Offset）
- ✅ HDF5 存储
- ✅ 单元测试（15/15 通过）

---

## 阶段 2：MODFLOW Stage 2 数据生成 🎯

**目标**：生成 Text-to-Computation 训练数据

**状态**：🚧 待实现（当前优先级 P0）

**输出**：
```json
// data/modflow/text2comp_training.jsonl
{"text": "水力传导系数为 15.3 m/day，储水系数 0.12，抽水量 -200 m³/day，初始水头 7.5 m，补给量 0.0008 m/day", "params": [15.3, 0.12, -200.0, 7.5, 0.0008], "param_names": ["hk", "sy", "pumping", "strt", "rch"]}
{"text": "含水层的水力传导系数设为 28 米每天，储水系数取 0.18，中心井抽水速率 -350 立方米每天，初始水位 6.2 米，面状补给 0.0015 米每天", "params": [28.0, 0.18, -350.0, 6.2, 0.0015], "param_names": ["hk", "sy", "pumping", "strt", "rch"]}
...
```

### 需要实现的模块

#### 1. 语言模板库 (`text_generators/template_bank.py`)

**模板类型**：

```python
# 类型 1: 直译模板（技术风格）
templates_direct = [
    "水力传导系数为 {hk} m/day，储水系数 {sy}，抽水量 {pumping} m³/day，初始水头 {strt} m，补给量 {rch} m/day",
    "K = {hk} 米每天，Sy = {sy}，Q = {pumping} 立方米每天，初始水位 {strt} 米，补给 {rch} 米每天",
    "hk={hk}, sy={sy}, pumping={pumping}, strt={strt}, rch={rch}",
]

# 类型 2: 自然语言模板（描述风格）
templates_natura含水层的水力传导系数设为 {hk} 米每天，储水系数取 {sy}，中心井抽水速率 {pumping} 立方米每天，初始水位 {strt} 米，面状补给 {rch} 米每天",
    "地下水模型参数配置如下：渗透率 {hk} m/d，比储水率 {sy}，井流量 {pumping} m³/d，起始水头 {strt} m，降雨入渗 {rch} m/d",
    "该含水层的渗透性能参数为 {hk} 米/天，储水能力系数为 {sy}，抽水井日抽水量 {pumping} 立方米，模拟初始水头高程 {strt} 米，区域补给强度 {rch} 米/天",
]

# 类型 3: 简化模板（代码风格）
templates_simplified = [
    "K={hk}, Sy={sy}, Q={pumping}, h0={strt}, R={rch}",
    "hk {hk}, sy {sy}, pumping {pumping}, strt {strt}, rch {rch}",
    "{hk} {sy} {pumping} {strt} {rch}",
]

# 类型 4: 顺序变换模板
# 随机打乱参数顺序
templates_permuted = [
    "初始水头 {strt} m，抽水量 {pumping} m³/day，水力传导系数 {hk} m/day，补给量 {rch} m/day，储水系数 {sy}",
    "补给量 {rch} m/day，储水系数 {sy}，初始水头 {strt} m，水力传导系数 {hk} m/day，抽水量 {pumping} m³/day",
]
```

**目标**：至少 **20 种不同模板**，覆盖多种表达方式

#### 2. 文本增强器 (`text_generators/augmentation.py`)

**增强策略**：

```python
# 1. 同义词替换
synonyms = {
    "水力传导系数": ["渗透率", "K值", "导水系数", "传导性能"],
    "储水系数": ["比储水率", "储水能力", "Sy", "储存系数"],
    "抽水量": ["井流量", "抽水速率", "开采量", "Q"],
    "初始水头": ["初始水位", "起始水头", "初始高程", "h0"],
    "补给量": ["降雨入渗", "补给强度", "面状补给", "R"],
}

# 2. 单位变换
unit_variants = {
    "m/day": ["米每天", "米/天", "m/d", "米·天⁻¹"],
    "m³/day": ["立方米每天", "立方米/天", "m³/d", "方每天"],
    "m": ["米", "m", "公尺"],
}

# 3. 数值格式
# 15.3 → "15.3" / "15.30" / "1.53×10¹" / "十五点三"

# 4. 参数名称变换
# "水力传导系数为 15.3" → "K为15.3" → "K=15.3" → "K: 15.3"
```

#### 3. 文本-参数对生成器 (`text_generators/modflow_text_generator.py`)

**核心函数**：

```python
def generate_text_param_pairs(
    params_array: np.ndarray,      # [N, n_params] 从 Stage 1 加载
    param_names: list[str],
    templates: list[str],
    augment: bool = True,
    seed: int = 42,
) -> list[dict]:
    """
    为数值参数生成对应的文本描述。

    Args:
        params_array: Stage 1 生成的参数矩阵
        param_names: 参数名称列表
        templates: 语言模板列表
        augment: 是否应用文本增强
        seed: 随机种子

    Returns:
        [
            {
                "text": "水力传导系数为 15.3 m/day，...",
                "params": [15.3, 0.12, -200.0, 7.5, 0.0008],
                "param_names": ["hk", "sy", "pumping", "strt", "rch"]
            },
            ...
        ]
    """
    pass
```

#### 4. Stage 2 管线 (`pipeline/text2comp_pipeline.py`)

**流程**：

```python
def run_text2comp_pipeline(cfg_path: str) -> str:
    """
    执行 Stage 2 数据生成管线。

    流程：
    1. 从 Stage 1 HDF5 文件加载参数矩阵
    2. 加载语言模板库
    3. 为每个参数样本生成多个文本变体
    4. 应用文本增强（同义词、单位、格式）
    5. 质量检查（文本长度、格式正确性）
    6. 导出为 JSONL 格式

    Returns:
        输出 JSONL 文件路径
    """
    pass
```

### 配置文件 (`configs/data_synthesis/text2comp.yaml`)

```yaml
# Stage 2: Text-to-Computation 数据生成配置

# 输入数据
input_h5: data/modflow/groundwater_timeseries.h5

# 输出路径
output_dir: data/modflow
output_file: text2comp_training.jsonl

# 模板配置
templates:
  use_direct: true          # 使用直译模板
  use_natural: true         # 使用自然语言模板
  use_simplified: true      # 使用简化模板
  use_permuted: true        # 使用顺序变换模板
  samples_per_param: 5      # 每个参数样本生成多少个文本变体

# 文本增强
augmentation:
  enable: true
  synonym_prob: 0.3         # 同义词替换概率
  unit_variant_prob: 0.3    # 单位变换概率
  format_variant_prob: 0.2  # 数值格式变换概率

# 质量检查
validation:
  min_text_length: 20       # 最短文本长度（字符）
  max_text_length: 500      # 最长文本长度
  check_param_coverage: true # 检查是否覆盖所有参数

# 随机种子
seed: 42
```

### 预期输出

```bash
# 运行 Stage 2 管线
python -m data_synthesis.pipeline.text2comp_pipeline \
    --config configs/data_synthesis/text2comp.yaml

# 输出统计
# ===== Text-to-Computation 数据生成完成 =====
# 输入样本数: 1000
# 生成文本样本数: 5000 (每个参数样本 5 个文本变体)
# 模板分布:
#   - 直译模板: 1250 (25%)
#   - 自然语言模板: 1250 (25%)
#   - 简化模板: 1250 (25%)
#   - 顺序变换模板: 1250 (25%)
# 文本增强应用率: 68%
# 输出文件: data/modflow/text2comp_training.jsonl
```

---

## 阶段 3：MODFLOW Stage 3 数据生成 🎯

**目标**：生成 Token Router 训练数据

**状态**：🚧 待实现（当前优先级 P1）

**输出**：
```json
// data/modflow/router_training.jsonl
{
  "question": "预测未来一年的地下水位变化，已知水力传导系数 15 m/day，储水系数 0.12，抽水量 -200 m³/day，初始水头 7.5 m，补给量 0.0008 m/day",
  "cot_trajectory": [
    {"token": "根据", "route": "continue"},
    {"token": "给定", "route": "continue"},
    {"token": "参数", "route": "continue"},
    ...
    {"token": "<call_expert>", "route": "expert_modflow", "expert_input": [15.0, 0.12, -200.0, 7.5, 0.0008]},
    {"token": "专家", "route": "continue"},
    {"token": "返回", "route": "continue"},
    ...
  ],
  "expert_calls": [
    {
      "position": 10,
      "expert_name": "modflow",
      "expert_input": [15.0, 0.12, -200.0, 7.5, 0.0008],
      "expert_output": [7.5, 7.48, 7.45, ..., 6.82]
    }
  ]
}
```

### 需要实现的模块

#### 1. CoT 轨迹生成器 (`trajectory_generators/cot_generator.py`)

**策略**：使用 LLM（GPT-4 或 Claude）生成包含专家调用的推理轨迹

**Prompt 模板**：

```python
SYSTEM_PROMPT = """
你是一个科学推理助手，可以调用物理模拟专家来辅助推理。

当你需要进行数值计算时，使用以下格式调用专家：
<call_expert name="modflow" input="[hk, sy, pumping, strt, rch]">

专家会返回计算结果，你需要基于结果继续推理。
"""

USER_PROMPT_TEMPLATE = """
问题：{question}

已知参数：
- 水力传导系数 (hk): {hk} m/day
- 储水系数 (sy): {sy}
- 抽水量 (pumping): {pumping} m³/day
- 初始水头 (strt): {strt} m
- 补给量 (rch): {rch} m/day

请生成完整的推理过程，包括：
1. 分析问题
2. 识别需要调用的专家
3. 调用专家（插入 <call_expert> 标记）
4. 基于专家返回的结果继续推理
5. 得出结论
"""
```

**核心函数**：

```python
def generate_cot_with_expert_calls(
    questions: list[str],
    params_array: np.ndarray,
    expert_outputs: np.ndarray,
    llm_model: str = "gpt-4",
    api_key: str = None,
) -> list[dict]:
    """
    生成包含专家调用的 CoT 推理轨迹。

    Args:
        questions: 问题列表
        params_array: 专家输入参数 [N, n_params]
        expert_outputs: 专家输出结果 [N, n_wells, n_timesteps]
        llm_model: 用于生成 CoT 的 LLM
        api_key: LLM API 密钥

    Returns:
        [
            {
                "question": "...",
                "cot_trajectory": [...],
                "expert_calls": [...]
            },
            ...
        ]
    """
    pass
```

#### 2. 路由标签标注器 (`trajectory_generators/route_labeler.py`)

**功能**：从 LLM 生成的文本中提取路由标签

```python
def parse_expert_calls(cot_text: str) -> list[dict]:
    """
    从 CoT 文本中解析专家调用。

    示例输入：
    "根据给定参数，我需要调用地下水模拟专家。<call_expert name='modflow' input='[15.0, 0.12, -200.0, 7.5, 0.0008]'> 专家返回的时序显示..."

    返回：
    [
        {
            "position": 10,  # <call_expert> 在 token 序列中的位置
            "expert_name": "modflow",
            "expert_input": [15.0, 0.12, -200.0, 7.5, 0.0008]
        }
    ]
    """
    pass

def tokenize_and_label(cot_text: str, expert_calls: list[dict]) -> list[dict]:
    """
    对 CoT 文本进行 token 化，并标注每个 token 的路由决策。

    返回：
    [
        {"token": "根据", "route": "continue"},
        {"token": "给定", "route": "continue"},
        ...
        {"token": "<call_expert>", "route": "expert_modflow", "expert_input": [...]},
        ...
    ]
    """
    pass
```

#### 3. 问题生成器 (`trajectory_generators/question_generator.py`)

**功能**：为每个参数样本生成多样化的问题

```python
question_templates = [
    "预测未来一年的地下水位变化，已知{params_text}",
    "给定含水层参数{params_text}，计算观测井的水头时序",
    "某地下水系统的参数为{params_text}，请模拟其水位动态",
    "分析以下地下水模型的水位变化趋势：{params_text}",
]
```

#### 4. Stage 3 管线 (`pipeline/router_pipeline.py`)

**流程**：

```python
def run_router_pipeline(cfg_path: str) -> str:
    """
    执行 Stage 3 数据生成管线。

    流程：
    1. 从 Stage 1 加载参数和专家输出
    2. 从 Stage 2 加载文本描述（用于生成问题）
    3. 为每个样本生成问题
    4. 调用 LLM 生成 CoT 轨迹
    5. 解析专家调用位置
    6. Token 化并标注路由标签
    7. 质量检查（专家调用数量、轨迹完整性）
    8. 导出为 JSONL 格式

    Returns:
        输出 JSONL 文件路径
    """
    pass
```

### 配置文件 (`configs/data_synthesis/router.yaml`)

```yaml
# Stage 3: Token Router 数据生成配置

# 输入数据
input_h5: data/modflow/groundwater_timeseries.h5
input_text2comp: data/modflow/text2comp_training.jsonl

# 输出路径
output_dir: data/modflow
output_file: router_training.jsonl

# LLM 配置
llm:
  model: gpt-4                # 或 claude-3-opus
  api_key_env: OPENAI_API_KEY # 从环境变量读取
  temperature: 0.7
  max_tokens: 2000

# 问题生成
question_generation:
  templates_per_sample: 3     # 每个样本生成多少个问题变体
  use_stage2_text: true       # 是否使用 Stage 2 生成的文本

# 质量检查
validation:
  min_expert_calls: 1         # 每个轨迹至少调用专家次数
  max_expert_calls: 3         # 每个轨迹最多调用专家次数
  check_trajectory_complete: true  # 检查轨迹完整性

# 随机种子
seed: 42
```

---

## 阶段 4：MODFLOW 完整管线集成与验证 🎯

**目标**：串联 Stage 1/2/3，形成端到端管线

**状态**：🚧 待实现（当前优先级 P2）

### 一键运行脚本 (`scripts/data_synthesis/run_modflow_full.sh`)

```bash
#!/bin/bash
# MODFLOW 完整三阶段数据生成

set -e

echo "===== MODFLOW 三阶段数据生成启动 ====="

# Stage 1: 专家模型数据
echo "Stage 1: 生成专家模型训练数据..."
python -m data_synthesis.pipeline.modflow_pipeline \
    --config configs/data_synthesis/modflow.yaml

# Stage 2: Text-to-Computation 数据
echo "Stage 2: 生成 Text-to-Computation 训练数据..."
python -m data_synthesis.pipeline.text2comp_pipeline \
    --config configs/data_synthesis/text2comp.yaml

# Stage 3: Token Router 数据
echo "Stage 3: 生成 Token Router 训练数据..."
python -m data_synthesis.pipeline.router_pipeline \
    --config configs/data_synthesis/router.yaml

echo "===== 三阶段数据生成完成 ====="
echo "输出文件："
echo "  - data/modflow/groundwater_timeseries.h5"
echo "  - data/modflow/text2comp_training.jsonl"
echo "  - data/modflow/router_training.jsonl"
```

### 数据质量验证脚本 (`scripts/data_synthesis/validate_modflow_data.py`)

```python
"""
验证 MODFLOW 三阶段数据的质量和一致性。

检查项：
1. Stage 1 数据格式正确性
2. Stage 2 文本-参数对的一致性
3. Stage 3 轨迹中专家调用的正确性
4. 三阶段数据之间的对应关系
"""
```

---

## 里程碑时间表

| 阶段 | 目标 | 状态 |
|------|------|------|
| Stage 1 | MODFLOW 专家数据生成 | ✅ 完成（14 个场景，6,600 样本）|
| Stage 2 | MODFLOW Text2Comp 数据 | ✅ 完成（33,000 训练对）|
| Stage 3 | MODFLOW Router 数据 | 🎯 下一步 |
| Stage 4 | 完整管线集成 | 🚧 待开始 |

---

## 关键原则

1. **深度优先**：先把 MODFLOW 做通，再扩展其他任务
2. **质量优先**：每个阶段都要有充分的测试和验证
3. **文档驱动**：先设计数据格式和接口，再实现代码
4. **模块化**：Stage 1/2/3 独立可运行，便于调试
5. **可复现**：所有随机过程设置种子，LLM 调用记录 Prompt

---

## 当前行动项

### 立即开始（P0）
- [ ] 实现 `text_generators/template_bank.py`（20+ 模板）
- [ ] 实现 `text_generators/augmentation.py`（文本增强）
- [ ] 实现 `text_generators/modflow_text_generator.py`（主生成器）
- [ ] 实现 `pipeline/text2comp_pipeline.py`（Stage 2 管线）
- [ ] 编写 Stage 2 单元测试
- [ ] 创建 `configs/data_synthesis/text2comp.yaml`

### 后续跟进（P1）
- [ ] 实现 `trajectory_generators/cot_generator.py`（LLM 集成）
- [ ] 实现 `trajectory_generators/route_labeler.py`（标签解析）
- [ ] 实现 `trajectory_generators/question_generator.py`（问题生成）
- [ ] 实现 `pipeline/router_pipeline.py`（Stage 3 管线）
- [ ] 编写 Stage 3 单元测试
- [ ] 创建 `configs/data_synthesis/router.yaml`

### 最后完善（P2）
- [ ] 编写一键运行脚本
- [ ] 编写数据质量验证脚本
- [ ] 完善文档和使用示例
- [ ] 性能优化（多进程、缓存）
