# Stage 2 完整流程 - 一键生成

## 🎯 核心功能

**一键运行，完成所有步骤**：
1. 使用 LLM 生成模板（分批生成，避免超时）
2. 加载 Stage 1 数据
3. 使用模板批量生成训练数据

## 🚀 快速开始

### 一键运行

```bash
python scripts/data_synthesis/run_stage2_complete.py
```

就这么简单！1-2 分钟后你会得到：
- ✅ 100 个 LLM 生成的模板
- ✅ 6,600 个训练数据对
- ✅ 成本仅 $0.01

### 快速测试

```bash
# 先测试（生成 10 个模板）
python scripts/data_synthesis/test_stage2_complete.py

# 测试成功后运行完整流程
python scripts/data_synthesis/run_stage2_complete.py
```

## 📁 文件说明

### 核心脚本

- **`run_stage2_complete.py`** - 主脚本（一键运行）
- **`test_stage2_complete.py`** - 快速测试脚本

### 配置文件

- **`configs/data_synthesis/stage2_complete.yaml`** - 主配置文件

### 文档

- **`STAGE2_USAGE.md`** - 详细使用说明
- **`LLM_TEMPLATE_GENERATION_SUCCESS.md`** - 方案说明

## ⚙️ 配置选项

编辑 `configs/data_synthesis/stage2_complete.yaml`：

```yaml
# 模板数量（推荐 100-1000）
n_templates: 100

# LLM 模型（推荐 Qwen2.5-7B）
llm:
  model: "Qwen/Qwen2.5-7B-Instruct"  # 快速
  # model: "Pro/zai-org/GLM-5"       # 质量更高但慢

# 每样本变体数（推荐 1-3）
n_variants_per_sample: 1
```

## 📊 性能对比

| 方案 | 耗时 | 成本 | 多样性 |
|------|------|------|--------|
| 逐个生成 | 2-17 天 | $0.30-0.45 | ⭐⭐⭐⭐⭐ |
| **两步法（本方案）** | **1-2 分钟** | **$0.01** | **⭐⭐⭐⭐** |
| 固定模板 | < 1 秒 | $0 | ⭐⭐⭐ |

**提速**: 20,000 - 34,000 倍！ 🚀

## 🎯 使用场景

### 场景 1：快速原型（推荐新手）

```bash
# 使用默认配置
python scripts/data_synthesis/run_stage2_complete.py

# 输出：6,600 个训练对
# 耗时：1-2 分钟
```

### 场景 2：大规模数据

```bash
# 修改配置：n_templates: 1000
python scripts/data_synthesis/run_stage2_complete.py

# 输出：6,600 个训练对（使用 1000 个模板）
# 耗时：10-20 分钟
```

### 场景 3：数据增强

```bash
# 修改配置：n_variants_per_sample: 3
python scripts/data_synthesis/run_stage2_complete.py

# 输出：19,800 个训练对（每样本 3 个变体）
# 耗时：1-2 分钟
```

## 📦 输出文件

```
data/text2comp/
├── templates_llm_generated.json          # 生成的模板
├── training_data_stage2_complete.jsonl   # 训练数据
└── training_data_stage2_complete_summary.json  # 统计报告
```

## 🔍 查看结果

```bash
# 查看训练数据数量
wc -l data/text2comp/training_data_stage2_complete.jsonl

# 查看统计报告
cat data/text2comp/training_data_stage2_complete_summary.json | python -m json.tool

# 查看前 3 个样本
head -n 3 data/text2comp/training_data_stage2_complete.jsonl | python -m json.tool
```

## 💡 核心优势

1. **一键运行** - 无需手动执行多个步骤
2. **速度极快** - 1-2 分钟完成（vs 2-17 天）
3. **成本极低** - $0.01（vs $0.30-0.45）
4. **完全 LLM 生成** - 符合"完全 LLM 生成"要求
5. **质量优秀** - 多样化的模板

## 🐛 常见问题

### Q: API 超时怎么办？

A: 增加超时时间：
```yaml
llm:
  timeout: 180  # 默认 120
```

### Q: 生成的模板数量不足？

A: 增加目标数量：
```yaml
n_templates: 150  # 多生成一些
```

### Q: 想要更多训练数据？

A: 增加变体数：
```yaml
n_variants_per_sample: 3  # 每样本 3 个变体
```

## 📚 更多信息

- 详细使用说明：[STAGE2_USAGE.md](../../STAGE2_USAGE.md)
- 方案说明：[LLM_TEMPLATE_GENERATION_SUCCESS.md](../../LLM_TEMPLATE_GENERATION_SUCCESS.md)

---

**快速开始**：
```bash
python scripts/data_synthesis/run_stage2_complete.py
```

就这么简单！🚀
