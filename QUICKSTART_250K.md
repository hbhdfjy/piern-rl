# 快速入门：生成250K样本数据集

本指南帮助您快速生成PiERN 250K样本的MODFLOW数据集。

---

## 前置条件

### 1. 安装依赖

```bash
# 安装Python包
pip install -r requirements.txt
pip install -e .

# 安装MODFLOW模拟器
pip install flopy
```

### 2. 设置环境变量（用于模板生成）

```bash
# 使用SiliconFlow API（推荐，便宜）
export SILICONFLOW_API_KEY="your_api_key_here"

# 或使用OpenAI API
export OPENAI_API_KEY="your_api_key_here"
```

---

## Step 1: 生成语言模板（2-4小时）

为25个场景各生成100条文本模板：

```bash
python -m piern.text2comp.template_generator
```

**预期输出**：
- `data/text2comp/scenario_templates.json`
- 2,500条模板（25场景 × 100模板）

**验证**：
```bash
# 检查模板文件
python -c "
import json
with open('data/text2comp/scenario_templates.json', 'r', encoding='utf-8') as f:
    templates = json.load(f)
print(f'场景数: {len(templates)}')
for scenario, tmpl_list in templates.items():
    print(f'  {scenario}: {len(tmpl_list)} 条模板')
"
```

**预计成本**：~$0.50

---

## Step 2: 测试单个场景（5-10分钟）

在批量生成前，先测试一个场景确保配置正确：

```bash
# 生成100个样本测试（快速验证）
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/variants/baseline.yaml \
    --override n_samples=100

# 检查输出
python scripts/modflow/inspect_data.py \
    data/modflow/baseline_groundwater_timeseries.h5
```

**预期输出**：
- `data/modflow/baseline_groundwater_timeseries.h5`
- 100个样本（或更多，如果启用了增强）

---

## Step 3: 批量生成Stage 1数据（20-40小时）

### 选项A：生成所有25个场景（推荐）

```bash
# 使用8核并行生成
python scripts/modflow/batch_generate.py \
    --skip-existing \
    --parallel 8
```

### 选项B：仅生成P0优先级场景（更快）

如果时间紧张，可以先生成最重要的场景：

```bash
# 创建优先级场景列表
cat > priority_scenarios.txt << EOF
baseline
low_permeability
medium_permeability
high_permeability
light_pumping
heavy_pumping
artificial_recharge
short_term_daily
medium_term_halfyear
long_term_twoyears
coarse_grid_10x10
fine_grid_40x40
arid_region
humid_region
urban_water_supply
multilayer_3layers
multilayer_5layers
heterogeneous_field
river_boundary
lake_boundary
seasonal_variation
EOF

# 批量生成（仅这21个场景）
python scripts/modflow/batch_generate.py \
    --scenarios priority_scenarios.txt \
    --parallel 8
```

### 监控进度

```bash
# 实时查看生成进度
watch -n 60 'ls -lh data/modflow/*.h5 | wc -l; du -sh data/modflow/'

# 查看详细信息
python scripts/utils/summarize_all.py
```

**预期输出**：
- `data/modflow/*.h5` - 25个HDF5文件
- 总样本数：250,000
- 总存储：~50 MB（压缩后）

**预计时间**：
- 单核：~140小时
- 8核并行：~18小时
- 16核并行：~9小时

---

## Step 4: 生成Stage 2文本对（10-30分钟）

使用预生成的模板填充参数值：

```bash
python -m piern.text2comp.pipeline_with_templates \
    --config configs/text2comp/default.yaml
```

**预期输出**：
- `data/text2comp/training_data_llm.jsonl`
- 250,000 文本-参数对
- `data/text2comp/data_summary_templates.json` - 统计摘要

**验证**：
```bash
# 检查文本对数量
wc -l data/text2comp/training_data_llm.jsonl

# 查看样例
head -n 3 data/text2comp/training_data_llm.jsonl | python -m json.tool

# 查看统计
cat data/text2comp/data_summary_templates.json
```

**预计成本**：$0（无LLM调用，仅模板填充）

---

## Step 5: 数据质量验证（30分钟）

### 检查Stage 1数据质量

```bash
# 检查每个场景
for file in data/modflow/*.h5; do
    echo "检查: $file"
    python scripts/modflow/inspect_data.py "$file" --brief
done

# 生成完整统计报告
python scripts/utils/summarize_all.py > data_summary_250k.txt
```

### 检查Stage 2数据质量

```bash
# 检查文本多样性
python scripts/text2comp/inspect_data.py \
    data/text2comp/training_data_llm.jsonl \
    --check-diversity

# 检查模板覆盖率
python -c "
import json
from collections import Counter

templates_used = []
with open('data/text2comp/training_data_llm.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        pair = json.loads(line)
        templates_used.append((pair['scenario'], pair['template_id']))

print(f'总文本对数: {len(templates_used)}')
print(f'唯一模板数: {len(set(templates_used))}')

# 按场景统计
scenario_counts = Counter([t[0] for t in templates_used])
print('\\n各场景文本对数:')
for scenario, count in sorted(scenario_counts.items()):
    print(f'  {scenario}: {count}')
"
```

---

## 常见问题

### Q1: 如何减少生成时间？

**方法1：使用更多CPU核心**
```bash
python scripts/modflow/batch_generate.py --parallel 16
```

**方法2：减少场景数量**
```bash
# 仅生成前10个场景
python scripts/modflow/batch_generate.py --max-scenarios 10
```

**方法3：降低每场景样本数**
```bash
# 临时降低为5000样本/场景
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/variants/baseline.yaml \
    --override n_samples=5000
```

### Q2: 如何恢复中断的生成？

使用 `--skip-existing` 标志：

```bash
python scripts/modflow/batch_generate.py \
    --skip-existing \
    --parallel 8
```

这会自动跳过已生成的文件。

### Q3: 如何验证数据物理一致性？

```bash
# 检查水量平衡
python scripts/modflow/validate_physics.py \
    data/modflow/baseline_groundwater_timeseries.h5

# 检查参数分布
python scripts/modflow/plot_param_distribution.py \
    data/modflow/
```

### Q4: 模板生成失败怎么办？

如果模板生成中断或质量不佳：

```bash
# 重新生成特定场景的模板
python -c "
from piern.text2comp.template_generator import TemplateGenerator, generate_scenario_descriptions
from piern.core.llm_client import LLMClient
import json
import os

llm = LLMClient(provider='siliconflow', model='Qwen/Qwen2.5-7B-Instruct', api_key=os.getenv('SILICONFLOW_API_KEY'))
generator = TemplateGenerator(llm)

# 重新生成 baseline 场景
templates = generator.generate_templates_for_scenario(
    'baseline',
    '标准地下水流动场景，中等渗透率，中等抽水强度',
    100
)

print(f'生成了 {len(templates)} 条模板')
"
```

### Q5: 如何自定义场景配置？

编辑 `configs/modflow/variants/<scenario>.yaml`：

```yaml
# 修改样本数
n_samples: 5000  # 降低到5000

# 修改参数范围
params:
  hk_min: 5.0
  hk_max: 20.0  # 缩小范围

# 禁用增强
augmentation:
  enabled: false
```

然后重新生成：

```bash
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/variants/<scenario>.yaml
```

---

## 下一步

完成数据生成后：

1. **数据发布**：
   ```bash
   # 压缩数据
   tar -czf piern_250k_data.tar.gz data/

   # 上传到GitHub Release或HuggingFace
   ```

2. **训练模型**：
   使用生成的数据训练PiERN的三个阶段模型

3. **论文写作**：
   参考 `SCALE_UP_PLAN_250K.md` 中的论文写作要点

---

## 资源需求

### 硬件要求

| 资源 | 最小配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4核 | 8-16核 |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 10 GB | 20 GB |
| 时间 | 40-80小时 | 18-24小时 |

### 软件要求

- Python 3.8+
- flopy（MODFLOW接口）
- numpy, scipy, h5py
- LLM API key（用于模板生成）

---

## 技术支持

遇到问题？

1. 查看详细文档：`SCALE_UP_PLAN_250K.md`
2. 查看实施路线图：`IMPLEMENTATION_ROADMAP.md`
3. 查看场景说明：`docs/modflow_scenarios.md`
4. 提交Issue：https://github.com/hbhdfjy/piern/issues

---

**文档版本**：v1.0
**创建时间**：2026-03-15
**适用版本**：piern v2.0（250K规模）
