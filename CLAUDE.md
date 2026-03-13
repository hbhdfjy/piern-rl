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

# Stage 1: 批量生成 MODFLOW 数据
python scripts/data_synthesis/batch_generate_modflow.py --skip-existing

# Stage 2: 生成 Text-to-Computation 训练数据（完全 LLM）
python scripts/data_synthesis/quick_test_api.py  # 快速测试
python scripts/data_synthesis/run_text2comp_llm.py --dry-run  # Dry-run
python scripts/data_synthesis/run_text2comp_llm.py  # 完整运行

# 检查数据
python scripts/data_synthesis/inspect_stage1_data.py data/modflow/baseline_groundwater_timeseries.h5
python scripts/data_synthesis/inspect_stage2_data.py data/text2comp/training_data_llm.jsonl
python scripts/data_synthesis/summarize_all_stage1_data.py

# 测试参数空间采样增强
python scripts/data_synthesis/test_parameter_augmentation.py
```

## 项目结构

### `data_synthesis/` — 数据合成管线
无需人工标注，自动为 PiERN 训练构建高质量数据集。

核心设计：
- `generators/` — 物理模拟器驱动的数据生成（当前：MODFLOW 地下水位）
  - 从参数空间采样
  - 调用物理模拟器正演
  - 输出时序数据
- `augmenters/` — 参数空间采样增强（V2）
  - 在参数邻域采样新参数（±5% 扰动）
  - 运行 MODFLOW 生成新时序
  - 保持物理一致性（不同参数 → 不同输出）
  - 提高模型精度 2-3 倍
- `validators/` — 质量过滤
  - 过滤 NaN/Inf 样本
  - 过滤常数序列（方差过小）
  - 过滤物理不合理值
- `pipeline/` — 端到端流程编排
  - `modflow_pipeline_v2.py` — Stage 1 数据生成（使用参数空间采样增强）
  - `text2comp_pipeline_llm.py` — Stage 2 完全 LLM 数据生成
  - 支持进度条、日志、元数据保存
- `text_generators/` — 完全 LLM 文本生成
  - `llm_client.py` — 统一的 LLM API 客户端
  - `llm_text_generator.py` — LLM 文本生成器（零模板依赖）
- `utils/` — 工具函数
  - HDF5 读写（压缩存储）

## 数据合成流程

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

## 任务支持

本仓库仅支持 **MODFLOW 地下水模拟任务**：

| 任务 | 状态 | 数据路径 | 输入参数 | Stage 1 输出 | Stage 2 输出 |
|------|------|----------|----------|--------------|--------------|
| MODFLOW 地下水位 | ✅ 已完成 | `data/modflow/` | 5 个标量（hk, sy, pumping, strt, rch）| 14 个 HDF5 文件<br>6,600 样本 | training_data_v2.jsonl<br>33,000 训练对 |

## 扩展新任务

要添加新任务的数据合成，需要：

1. **创建生成器**：在 `data_synthesis/generators/` 下实现 `<task>_generator.py`
   - 实现 `generate_sample()` 和 `generate_batch()` 函数
   - 调用物理模拟器或专家模型
   - 返回 (时序数据, 参数) 元组

2. **实现增强器**：在 `augmenters/` 下实现参数空间采样增强
   - 扰动参数后重新运行物理模拟
   - 保持物理一致性

3. **定制验证器**：在 `validators/` 下实现任务特定的质量检查

4. **创建管线**：在 `pipeline/` 下创建 `<task>_pipeline_v2.py`，串联上述模块

5. **添加配置**：在 `configs/data_synthesis/` 下创建 `<task>_v2.yaml`
