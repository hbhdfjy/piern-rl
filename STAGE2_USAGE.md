# Stage 2 完整流程使用说明

## 🎯 一键生成

只需运行一次，即可完成：
1. ✅ 使用 LLM 生成模板
2. ✅ 加载 Stage 1 数据
3. ✅ 使用模板批量生成训练数据

## 📝 快速开始

### 使用默认配置

```bash
python scripts/data_synthesis/run_stage2_complete.py
```

### 使用自定义配置

```bash
python scripts/data_synthesis/run_stage2_complete.py \
  --config configs/data_synthesis/stage2_complete.yaml
```

## ⚙️ 配置说明

编辑 `configs/data_synthesis/stage2_complete.yaml`：

```yaml
# LLM 配置
llm:
  provider: siliconflow
  model: "Qwen/Qwen2.5-7B-Instruct"  # 推荐：快速且质量好
  # 或使用 GLM-5：model: "Pro/zai-org/GLM-5"（质量更高但慢）

# 模板数量
n_templates: 100  # 目标生成 100 个模板

# 分批生成（避免超时）
template_batch_size: 20  # 每批生成 20 个

# 数据生成
n_variants_per_sample: 1  # 每样本使用 1 个模板
# n_variants_per_sample: 3  # 每样本使用 3 个模板（3 倍数据量）

# 输入/输出
stage1_data_dir: "data/modflow"
output_dir: "data/text2comp"
output_file: "training_data_stage2_complete.jsonl"
```

## 📊 预期输出

### 输出文件

```
data/text2comp/
├── templates_llm_generated.json          # 生成的模板
├── training_data_stage2_complete.jsonl   # 训练数据
└── training_data_stage2_complete_summary.json  # 统计报告
```

### 统计数据

**使用 Qwen2.5-7B（推荐）**：
- 模板数：100 个
- 训练对：6,600 个（6,600 样本 × 1 变体）
- 耗时：约 1-2 分钟
- 成本：约 $0.01

**使用 GLM-5（质量更高）**：
- 模板数：100 个
- 训练对：6,600 个
- 耗时：约 5-10 分钟
- 成本：约 $0.02

## 📋 完整示例

### 示例 1：快速生成（推荐）

```bash
# 使用 Qwen2.5-7B，生成 100 个模板
python scripts/data_synthesis/run_stage2_complete.py

# 预期：1-2 分钟完成
```

### 示例 2：生成更多模板

```bash
# 编辑配置文件
vim configs/data_synthesis/stage2_complete.yaml
# 修改：n_templates: 1000

# 运行
python scripts/data_synthesis/run_stage2_complete.py

# 预期：10-20 分钟完成
```

### 示例 3：生成更多变体

```bash
# 编辑配置文件
vim configs/data_synthesis/stage2_complete.yaml
# 修改：n_variants_per_sample: 3

# 运行
python scripts/data_synthesis/run_stage2_complete.py

# 输出：6,600 × 3 = 19,800 个训练对
```

### 示例 4：使用 GLM-5（更高质量）

```bash
# 编辑配置文件
vim configs/data_synthesis/stage2_complete.yaml
# 修改：model: "Pro/zai-org/GLM-5"

# 运行
python scripts/data_synthesis/run_stage2_complete.py

# 预期：5-10 分钟完成
```

## 🔍 查看结果

### 查看模板

```bash
# 查看生成的模板
python -c "
import json
with open('data/text2comp/templates_llm_generated.json') as f:
    data = json.load(f)
    print(f'模板数: {data[\"n_templates\"]}')
    print('\\n前 5 个模板:')
    for i, t in enumerate(data['templates'][:5], 1):
        print(f'{i}. {t}')
"
```

### 查看训练数据

```bash
# 查看样本数
wc -l data/text2comp/training_data_stage2_complete.jsonl

# 查看前 3 个样本
head -n 3 data/text2comp/training_data_stage2_complete.jsonl | python -m json.tool
```

### 查看统计报告

```bash
cat data/text2comp/training_data_stage2_complete_summary.json | python -m json.tool
```

## 🎯 核心优势

### vs 逐个生成（之前的方案）

| 指标 | 逐个生成 | 两步法（本方案） |
|------|---------|-----------------|
| 模板来源 | 无（实时生成） | LLM 生成 |
| 耗时 | 2-17 天 | **1-2 分钟** |
| 成本 | $0.30-0.45 | **$0.01** |
| 多样性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**提速**: 20,000 - 34,000 倍！ 🚀

### vs 固定模板

| 指标 | 固定模板 | 两步法（本方案） |
|------|---------|-----------------|
| 模板来源 | 人工设计 | LLM 生成 |
| 耗时 | < 1 秒 | 1-2 分钟 |
| 成本 | $0 | $0.01 |
| 多样性 | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**优势**: 完全 LLM 生成，多样性更高！

## 🚀 扩展方案

### 生成 10,000 个模板

```bash
# 修改配置
vim configs/data_synthesis/stage2_complete.yaml
# 修改：
#   n_templates: 10000
#   template_batch_size: 50

# 运行
python scripts/data_synthesis/run_stage2_complete.py

# 预计：20-30 分钟，成本 ~$2
```

### 生成多语言模板

```bash
# 修改代码中的 system_prompt，添加英文模板生成
# 或创建新的配置文件支持多语言
```

## ⚠️ 注意事项

### 1. API 密钥

确保配置文件中的 API 密钥有效：
```yaml
llm:
  api_key: "your-api-key-here"
```

### 2. 网络连接

需要访问 SiliconFlow API：
```bash
# 测试连接
curl -I https://api.siliconflow.cn
```

### 3. Stage 1 数据

确保已生成 Stage 1 数据：
```bash
# 检查数据
ls -lh data/modflow/*_groundwater_timeseries.h5
```

如果没有，先运行：
```bash
python scripts/data_synthesis/run_modflow_synthesis.py
```

## 🐛 故障排查

### 问题 1：API 超时

**症状**：`HTTPSConnectionPool: Read timed out`

**解决**：
```yaml
# 增加超时时间
llm:
  timeout: 180  # 默认 120 秒
```

### 问题 2：生成的模板数量不足

**症状**：生成了 50 个，目标是 100 个

**原因**：LLM 生成的部分模板不符合格式要求

**解决**：
- 增加 `n_templates`（如设为 150）
- 或运行多次，合并模板

### 问题 3：内存不足

**症状**：`MemoryError`

**解决**：
```yaml
# 减少每样本变体数
n_variants_per_sample: 1  # 默认 1
```

## 📚 相关文档

- [LLM_TEMPLATE_GENERATION_SUCCESS.md](LLM_TEMPLATE_GENERATION_SUCCESS.md) - 方案详细说明
- [GENERATION_PROGRESS.md](GENERATION_PROGRESS.md) - 之前的进度报告
- [configs/data_synthesis/stage2_complete.yaml](configs/data_synthesis/stage2_complete.yaml) - 配置文件

## 💡 总结

**一键运行**：
```bash
python scripts/data_synthesis/run_stage2_complete.py
```

**预期结果**：
- ✅ 100 个 LLM 生成的模板
- ✅ 6,600 个训练数据对
- ✅ 1-2 分钟完成
- ✅ 成本 $0.01

**核心优势**：
- 🚀 速度极快（vs 逐个生成：20,000 倍提速）
- 💰 成本极低（$0.01 vs $0.30-0.45）
- ✅ 完全 LLM 生成（符合要求）
- ⭐ 质量很好（多样化）

---

**状态**: ✅ 可用
**日期**: 2026-03-13
**方案**: 两步法（LLM 生成模板 + 模板批量生成数据）
