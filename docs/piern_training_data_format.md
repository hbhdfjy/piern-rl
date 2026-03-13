# PiERN 训练数据格式详解

## 概述

PiERN 数据合成管线不仅要生成物理模拟数据（如地下水位时序），更重要的是要将这些数据转化为 PiERN 三阶段训练所需的标注格式。

## PiERN 三阶段训练回顾

### Stage 1: 专家模型预训练
- **目标**：训练物理隔离的专家模型（FNO、SoH 神经网络等）
- **数据需求**：纯数值数据（输入参数 → 输出时序）
- **训练后状态**：专家模型**永远冻结**

### Stage 2: Text-to-Computation 训练
- **目标**：训练 Qwen3-0.6B 解码器，将自然语言映射为专家所需的数值输入张量
- **数据需求**：(文本描述, 数值参数) 样本对

### Stage 3: Token Router 训练
- **目标**：训练轻量级分类器，决定何时调用专家
- **数据需求**：(LLM 隐层状态, 路由决策标签) 样本对

## 数据合成管线的完整职责

```
物理模拟数据生成
    ↓
质量过滤 + 扰动增强
    ↓
【关键】转化为 PiERN 训练格式
    ├─→ Stage 1 数据：(数值参数, 时序输出)
    ├─→ Stage 2 数据：(文本描述, 数值参数)
    └─→ Stage 3 数据：(CoT 轨迹, 路由标签)
```

## Stage 1 数据格式（已实现）

### 当前输出格式
```python
# data/modflow/groundwater_timeseries.h5
{
    "timeseries": [N, n_wells, n_timesteps],  # 专家模型输出
    "params": [N, n_params],                   # 专家模型输入
    "param_names": ["hk", "sy", "pumping", "strt", "rch"]
}
```

### 用途
- 训练专家模型：`expert(params) → timeseries`
- MODFLOW 任务：5 个标量参数 → 5 个观测井 × 365 天水头时序
- 训练完成后，专家模型冻结，不再更新

### ✅ 状态：已实现

---

## Stage 2 数据格式（待实现）

### 目标
训练 Text-to-Computation 模块，将自然语言描述映射为专家模型的数值输入。

### 数据格式
```python
# data/modflow/text2comp_training.jsonl
[
    {
        "text": "水力传导系数为 15.3 m/day，储水系数 0.12，抽水量 -200 m³/day，初始水头 7.5 m，补给量 0.0008 m/day",
        "params": [15.3, 0.12, -200.0, 7.5, 0.0008],
        "param_names": ["hk", "sy", "pumping", "strt", "rch"]
    },
    {
        "text": "含水层的水力传导系数设为 28 米每天，储水系数取 0.18，中心井抽水速率 -350 立方米每天，初始水位 6.2 米，面状补给 0.0015 米每天",
        "params": [28.0, 0.18, -350.0, 6.2, 0.0015],
        "param_names": ["hk", "sy", "pumping", "strt", "rch"]
    },
    ...
]
```

### 语言模板生成策略

#### 1. 直译模板（Direct Translation）
```python
templates = [
    "水力传导系数为 {hk} m/day，储水系数 {sy}，抽水量 {pumping} m³/day，初始水头 {strt} m，补给量 {rch} m/day",
    "K = {hk} 米每天，Sy = {sy}，Q = {pumping} 立方米每天，初始水位 {strt} 米，补给 {rch} 米每天",
]
```

#### 2. 自然语言模板（Natural Language）
```python
templates = [
    "含水层的水力传导系数设为 {hk} 米每天，储水系数取 {sy}，中心井抽水速率 {pumping} 立方米每天，初始水位 {strt} 米，面状补给 {rch} 米每天",
    "地下水模型参数配置如下：渗透率 {hk} m/d，比储水率 {sy}，井流量 {pumping} m³/d，起始水头 {strt} m，降雨入渗 {rch} m/d",
]
```

#### 3. 简化模板（Simplified）
```python
templates = [
    "K={hk}, Sy={sy}, Q={pumping}, h0={strt}, R={rch}",
    "hk {hk}, sy {sy}, pumping {pumping}, strt {strt}, rch {rch}",
]
```

#### 4. 顺序变换（Order Permutation）
随机打乱参数顺序，提升模型鲁棒性：
```python
"初始水头 {strt} m，抽水量 {pumping} m³/day，水力传导系数 {hk} m/day，补给量 {rch} m/day，储水系数 {sy}"
```

### 数据增强策略
- **同义词替换**：水力传导系数 ↔ 渗透率 ↔ K 值
- **单位变换**：m/day ↔ 米每天 ↔ 米/天
- **数值格式**：15.3 ↔ 15.30 ↔ 1.53e1
- **参数顺序**：随机排列 5 个参数的描述顺序

### 实现模块（待开发）
```python
# piern/text2comp/modflow_text_generator.py

def generate_text_param_pairs(
    params_array: np.ndarray,      # [N, n_params]
    param_names: list[str],
    templates: list[str],
    augment: bool = True,
) -> list[dict]:
    """
    为数值参数生成对应的文本描述。

    Returns:
        [{"text": "...", "params": [...], "param_names": [...]}, ...]
    """
    pass
```

### ❌ 状态：待实现

---

## Stage 3 数据格式（待实现）

### 目标
训练 Token Router，决定在 LLM 生成的每个 token 时间步是否调用专家。

### 核心思想
从完整的 CoT（Chain-of-Thought）推理轨迹中，自动标注哪些位置需要调用专家。

### 数据格式
```python
# data/modflow/router_training.jsonl
[
    {
        "question": "预测未来一年的地下水位变化，已知水力传导系数 15 m/day，储水系数 0.12，抽水量 -200 m³/day，初始水头 7.5 m，补给量 0.0008 m/day",
        "cot_trajectory": [
            {"token": "根据", "route": "continue"},
            {"token": "给定", "route": "continue"},
            {"token": "参数", "route": "continue"},
            {"token": "，", "route": "continue"},
            {"token": "我", "route": "continue"},
            {"token": "需要", "route": "continue"},
            {"token": "调用", "route": "continue"},
            {"token": "地下水", "route": "continue"},
            {"token": "模拟", "route": "continue"},
            {"token": "专家", "route": "continue"},
            {"token": "。", "route": "continue"},
            {"token": "<call_expert>", "route": "expert_modflow", "expert_input": [15.0, 0.12, -200.0, 7.5, 0.0008]},
            {"token": "专家", "route": "continue"},
            {"token": "返回", "route": "continue"},
            {"token": "的", "route": "continue"},
            {"token": "时序", "route": "continue"},
            {"token": "显示", "route": "continue"},
            {"token": "...", "route": "continue"},
        ],
        "expert_calls": [
            {
                "position": 11,  # 第 11 个 token 位置调用专家
                "expert_name": "modflow",
                "expert_input": [15.0, 0.12, -200.0, 7.5, 0.0008],
                "expert_output": [7.5, 7.48, 7.45, ..., 6.82]  # [n_wells * n_timesteps]
            }
        ]
    },
    ...
]
```

### 路由标签构造策略

#### 1. 基于关键词的启发式标注
```python
# 当 LLM 生成包含以下关键词时，标注为调用专家
keywords = ["调用专家", "运行模拟", "计算结果", "<call_expert>", "[EXPERT]"]
```

#### 2. 基于语义的标注
```python
# 当 LLM 生成的文本语义上表示"需要数值计算"时，标注为调用专家
# 例如："现在需要求解偏微分方程"、"计算地下水位时序"
```

#### 3. 合成 CoT 轨迹
使用 LLM（如 GPT-4）生成包含专家调用的推理轨迹：

**Prompt 示例**：
```
你是一个科学推理助手，可以调用物理模拟专家。

问题：预测未来一年的地下水位变化，已知水力传导系数 15 m/day，储水系数 0.12，抽水量 -200 m³/day，初始水头 7.5 m，补给量 0.0008 m/day。

请生成推理过程，在需要调用专家时插入 <call_expert> 标记。

输出格式：
1. 分析问题
2. 识别需要调用的专家
3. <call_expert name="modflow" input="[15.0, 0.12, -200.0, 7.5, 0.0008]">
4. 根据专家返回的结果继续推理
5. 得出结论
```

#### 4. 从真实对话中提取
如果有人类与 PiERN 交互的对话日志，可以从中提取真实的路由决策。

### 隐层状态提取
```python
# 在生成 CoT 轨迹时，记录 LLM 每个 token 的隐层状态
# 用于训练 Router: h_t → p(route | h_t)

{
    "token": "调用",
    "hidden_state": [768维向量],  # 从 LLM 最后一层提取
    "route": "continue"  # 或 "expert_modflow"
}
```

### 实现模块（待开发）
```python
# data_synthesis/trajectory_generators/cot_generator.py

def generate_cot_with_expert_calls(
    questions: list[str],
    params_array: np.ndarray,
    expert_outputs: np.ndarray,
    llm_model: str = "gpt-4",
) -> list[dict]:
    """
    生成包含专家调用的 CoT 推理轨迹。

    Args:
        questions: 问题列表
        params_array: 专家输入参数
        expert_outputs: 专家输出结果
        llm_model: 用于生成 CoT 的 LLM

    Returns:
        [{"question": "...", "cot_trajectory": [...], "expert_calls": [...]}, ...]
    """
    pass
```

### ❌ 状态：待实现

---

## 完整数据合成流程（更新后）

```
┌─────────────────────────────────────────┐
│  Step 1: 物理模拟数据生成                │
│  - 参数采样                              │
│  - MODFLOW/FNO 正演                      │
│  - 质量过滤 + 扰动增强                   │
│  输出: (params, timeseries)              │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Step 2: Stage 1 数据导出 ✅              │
│  - 保存为 HDF5 格式                      │
│  - 用于训练专家模型                       │
│  输出: groundwater_timeseries.h5         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Step 3: Stage 2 数据生成 ❌              │
│  - 语言模板生成                          │
│  - (文本描述, 数值参数) 样本对            │
│  - 同义词替换、单位变换、顺序打乱         │
│  输出: text2comp_training.jsonl          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Step 4: Stage 3 数据生成 ❌              │
│  - 合成 CoT 推理轨迹                     │
│  - 标注专家调用位置                       │
│  - 提取 LLM 隐层状态                     │
│  输出: router_training.jsonl             │
└─────────────────────────────────────────┘
```

## 项目结构（更新后）

```
piern/
├── data_synthesis/
│   ├── generators/
│   │   ├── modflow_generator.py           # ✅ 物理模拟数据生成
│   │   ├── pdebench_generator.py          # 🚧 待实现
│   │   └── ...
│   ├── text_generators/                   # ❌ 新增模块
│   │   ├── modflow_text_generator.py      # Stage 2: 文本-参数对生成
│   │   ├── template_bank.py               # 语言模板库
│   │   └── augmentation.py                # 文本增强（同义词、单位变换）
│   ├── trajectory_generators/             # ❌ 新增模块
│   │   ├── cot_generator.py               # Stage 3: CoT 轨迹生成
│   │   ├── route_labeler.py               # 路由标签自动标注
│   │   └── hidden_state_extractor.py      # 隐层状态提取
│   ├── augmenters/
│   │   └── perturbation.py                # ✅ 扰动增强
│   ├── validators/
│   │   └── quality_filter.py              # ✅ 质量过滤
│   ├── pipeline/
│   │   ├── modflow_pipeline.py            # ✅ Stage 1 管线
│   │   ├── text2comp_pipeline.py          # ❌ Stage 2 管线
│   │   └── router_pipeline.py             # ❌ Stage 3 管线
│   └── utils/
│       ├── hdf5_writer.py                 # ✅ HDF5 读写
│       └── jsonl_writer.py                # ❌ JSONL 读写
└── configs/
    └── data_synthesis/
        ├── modflow.yaml                   # ✅ Stage 1 配置
        ├── text2comp.yaml                 # ❌ Stage 2 配置
        └── router.yaml                    # ❌ Stage 3 配置
```

## 下一步实现优先级

### 高优先级（必需）
1. **Stage 2 数据生成**
   - 实现 `text_generators/` 模块
   - 构建语言模板库
   - 实现文本增强策略

2. **Stage 3 数据生成**
   - 实现 `trajectory_generators/` 模块
   - 集成 LLM API（GPT-4/Claude）生成 CoT
   - 实现路由标签自动标注

### 低优先级（增强）
3. **数据质量分析**
   - 文本多样性分析
   - 路由标签分布统计
   - 可视化工具

## 关键设计原则

1. **模块化**：Stage 1/2/3 数据生成相互独立，可单独运行
2. **可扩展**：语言模板、CoT 生成策略可配置、可插拔
3. **质量优先**：每个阶段都有质量检查和过滤机制
4. **自动化**：尽可能减少人工标注，利用 LLM 自动生成
5. **可复现**：所有随机过程都设置种子，确保可复现

## 总结

PiERN 数据合成管线的完整职责：
- ✅ **Stage 1 数据**：物理模拟 → (数值参数, 时序输出) → 训练专家模型
- ❌ **Stage 2 数据**：语言模板 → (文本描述, 数值参数) → 训练 Text2Comp
- ❌ **Stage 3 数据**：CoT 生成 → (推理轨迹, 路由标签) → 训练 Token Router

当前项目已完成 Stage 1 数据生成，接下来需要实现 Stage 2 和 Stage 3 的数据转化逻辑。
