# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作提供指导。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt
pip install -e .

# 运行所有测试
pytest tests/

# 运行单个测试文件
pytest tests/test_rl_training/test_reward.py -v

# 代码检查
ruff check .
```

## 项目结构

两个独立子项目共享同一个核心模块 `piern_core/`：

### `piern_core/` — 共享基础模块
包含两个子项目都会用到的三大 PiERN 组件：
- `models/experts.py` — 物理隔离的专家模型（FNO、SoH 神经网络、线性计算器）；Stage 1 训练完成后**永远冻结**
- `models/text2comp.py` — 基于 Qwen3-0.6B 微调的解码器，将自然语言映射为专家所需的数值输入张量
- `models/router.py` — 轻量级分类器，输入 LLM 隐层状态 `h_t`，输出专家集合 E 上的路由概率 `p(e | h_t)`

### 子项目1：`data_synthesis/` — 自动数据合成与增强
无需人工标注，自动为 PiERN 三阶段监督训练构建训练数据。

核心设计：
- `generators/` — 按任务生成（文本, 数值张量）样本对，使用语言模板
- `augmenters/` — 实现三种扰动策略：Identity、Scaling（`x' = x·k`）、Offset（`x' = x + b`）
- `validators/` — 过滤低质量样本（MSE 异常值、维度不匹配等）
- `pipeline/` — 串联合成 → 增强 → 验证 → 导出的完整流程

### 子项目2：`rl_training/` — 多轮强化学习
将 PiERN 推理过程建模为 MDP，通过 GRPO 对 Router 和 Text2Comp 进行策略优化（Stage 4，在监督 Stage 3 之后）。

核心设计：
- `env/` — 将完整 PiERN 推理循环封装为 gym 风格的环境；状态 = (token 上下文, 隐层状态, 调用历史)；动作 = {继续 LLM 生成 | 调用专家 e_i(输入 x)}
- `reward/` — 按任务实现奖励函数：PDEBench 用 RMSE，BMS 用利润公式，GCAM 用政策对齐分数
- `algorithms/` — GRPO（主要）、PPO、REINFORCE；优先使用 GRPO，无需额外 Critic 网络
- `trainer/` — 执行 rollout → 计算奖励 → 更新参数的训练循环，含 KL 约束防止语言能力退化

## 架构约束

- 专家模型**永远冻结**，两个子项目均不对其反向传播
- 数据合成阶段 LLM 主干冻结；RL 阶段仅通过 LoRA 微调 LLM 主干
- RL 是第四阶段，必须以 Stage 3 的检查点作为初始化，不能从零开始
- RL 训练过程中需持续监控 MMLU/GLUE 分数，及时发现语言能力退化

## 实验任务

| 任务 | 数据路径 | 专家类型 | 奖励信号 |
|------|----------|----------|----------|
| PDEBench | `data/pdebench/` | 3 个 FNO 模型（每个 PDE 一个）| RMSE vs 真值 |
| GCAM | `data/gcam/` | 9 个领域神经代理 | 政策对齐分数 |
| BMS | `data/bms/` | SoH 神经网络 + 线性利润公式 | `R = Δp·P - α·c_a·1200` |

**建议从 BMS 开始验证 RL**：两步调用链（SoH → 利润）、奖励信号清晰、数据集小、迭代快。
