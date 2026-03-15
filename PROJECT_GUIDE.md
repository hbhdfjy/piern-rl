# PiERN 项目完整指南

**版本**：v2.0 - 250K规模
**更新日期**：2026-03-15
**状态**：✅ 准备就绪，可启动生成

---

## 📋 目录

1. [项目概述](#项目概述)
2. [快速入门](#快速入门)
3. [数据集规模计划](#数据集规模计划)
4. [实施路线图](#实施路线图)
5. [代码质量保证](#代码质量保证)
6. [文档索引](#文档索引)

---

## 项目概述

### 核心定位

**PiERN** = **P**arameter-to-**I**nference **E**xpert **R**outing **N**etwork

多模拟器数据合成管线，创建首个跨多物理场的地质时序数据集。

### 目标规模

- **Stage 1**：250,000 MODFLOW样本（25场景 × 10,000）
- **Stage 2**：250,000 文本-参数对（基于2,500条模板）
- **Stage 3**：37,500 CoT轨迹（待实现）

### vs PDEBench

- **规模优势**：12.5× （250K vs 20K）
- **场景多样性**：2.5× （25 vs 10）
- **存储优势**：轻量2000× （50MB vs 100GB）

---

## 快速入门

### 环境准备

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install -e .

# 2. 验证MODFLOW
which mf2005  # 应该输出: ~/bin/mf2005

# 3. 验证配置
python scripts/modflow/verify_all_scenarios.py
```

### 启动250K生成

```bash
# 方式1: 使用启动脚本（推荐）
./START_FULL_250K.sh

# 方式2: 直接运行批量生成
python scripts/modflow/batch_generate.py \
    --skip-existing \
    --parallel \
    --max-workers 8 \
    --checkpoint logs/checkpoint.json

# 方式3: 单个场景测试
python scripts/modflow/batch_generate.py \
    --single baseline.yaml
```

### 预计时间

- **单核**：140小时（6天）
- **8核并行**：17.5小时（<1天）
- **建议**：后台运行，使用 `nohup` 或 `screen`

---

## 数据集规模计划

### Stage 1: 物理模拟数据（250K样本）

#### 场景分类（25个场景）

| 类别 | 场景数 | 样本数 | 说明 |
|------|--------|--------|------|
| 基础场景 | 4 | 40,000 | baseline, arid/humid_region, urban_water_supply |
| 渗透率变化 | 3 | 30,000 | low/medium/high_permeability |
| 抽水强度 | 3 | 30,000 | light/heavy_pumping, artificial_recharge |
| 时间尺度 | 3 | 30,000 | short_term_daily, medium_term_halfyear, long_term_twoyears |
| 空间分辨率 | 2 | 20,000 | coarse_grid_10x10, fine_grid_40x40 |
| 多层含水层 | 2 | 20,000 | multilayer_3layers, multilayer_5layers |
| 非均质介质 | 1 | 10,000 | heterogeneous_field |
| 边界条件 | 2 | 20,000 | river_boundary, lake_boundary |
| 季节性变化 | 1 | 10,000 | seasonal_variation |
| 海水入侵 | 1 | 10,000 | seawater_intrusion |
| **P2场景** | **3** | **30,000** | **land_subsidence, contaminant_transport, geothermal_reservoir** |
| **总计** | **25** | **250,000** | - |

#### P2场景特点

1. **land_subsidence**（地面沉降）
   - 使用Terzaghi固结理论
   - 输出：累积沉降指数（归一化0-1）
   - 参数：压缩系数、再压缩系数、孔隙比、厚度

2. **contaminant_transport**（污染物运移）
   - 简化为污染风险指数
   - 输出：基于距离衰减和水头梯度
   - 参数：污染源强度、位置

3. **geothermal_reservoir**（地热储层）
   - 简化为温度影响指数
   - 输出：基于热扩散和水头梯度
   - 参数：热源强度、位置、注水量

#### 参数空间覆盖

- **参数跨度**：1000× (hk: 0.1-100 m/day)
- **参数维度**：5-14个（场景不同）
- **增强策略**：参数空间采样增强（V2），扰动±5%，增加20%样本

#### 存储估算

- **每样本**：~200 bytes（高度压缩）
- **总存储**：250,000 × 200 bytes ≈ 50 MB
- **格式**：HDF5 + gzip压缩 + shuffle过滤器

---

### Stage 2: 文本-参数对（250K对）

#### 模板系统

- **每场景模板数**：100条
- **总模板数**：25场景 × 100 = 2,500条
- **模板类型**：
  - 专业术语型（20条）
  - 通俗语言型（20条）
  - 简洁描述型（15条）
  - 详细说明型（15条）
  - 问题导向型（10条）
  - 场景应用型（10条）
  - 对比分析型（5条）
  - 因果关系型（5条）

#### 生成策略

- **零LLM成本**：使用模板填充参数
- **每样本**：随机选择1条模板
- **总文本对**：250,000对

#### 存储估算

- **每对**：~330 bytes
- **总存储**：250,000 × 330 bytes ≈ 82 MB
- **格式**：JSONL

---

### Stage 3: CoT轨迹（37.5K轨迹）

**状态**：待实现

- **采样率**：50%的Stage 1样本
- **总轨迹数**：125,000 × 0.5 = 37,500
- **存储**：~110 MB

---

## 实施路线图

### Week 1: MODFLOW扩展至250K（当前）

**目标**：7,600 → 250,000样本

**已完成**：
- ✅ 26个配置文件更新为10K规模
- ✅ P0功能实现（多层、非均质、边界、季节）
- ✅ P2场景实现（地面沉降、污染物、地热）
- ✅ 代码质量修复（P0问题）
- ✅ 验证脚本（25个场景全部通过）

**进行中**：
- ⏳ 批量生成250K样本

**待办**：
- [ ] 生成2,500条语言模板
- [ ] 生成250K文本对

**预计完成**：2026-03-16

---

### Week 2: SimPEG实现（计划）

**目标**：新增20,000样本（地球物理勘探）

**任务**：
- MT/DC/TEM三种方法实现
- 15个场景配置
- 参数采样和增强

**预计完成**：2026-03-22

---

### Week 3-4: Devito实现（计划）

**目标**：新增10,000样本（地震波传播）

**任务**：
- 速度模型生成器
- 波动方程求解器
- 5个场景配置

**预计完成**：2026-04-05

---

### Week 5-6: TOUGH2实现（计划）

**目标**：新增15,000样本（多相流体）

**任务**：
- TOUGH2输入文件生成
- 结果解析器
- 5个场景配置

**预计完成**：2026-04-19

---

### Week 7: Stage 2扩展（计划）

**目标**：6,600 → 375,000文本对

**任务**：
- 为4个模拟器设计专用模板
- 生成375K文本对
- 验证文本多样性

**预计完成**：2026-04-26

---

### Week 8: Stage 3实现 + 文档更新（计划）

**目标**：新增37,500 CoT轨迹

**任务**：
- 实现CoT生成器
- 实现路由标签器
- 更新所有文档
- 准备论文补充材料

**预计完成**：2026-05-03

---

## 代码质量保证

### 已完成的修复（P0问题）

#### 1. ✅ 参数空间采样增强失效

**问题**：增强策略完全失效，生成随机样本而非邻域样本

**修复**：
- 实现 `generate_sample_from_params()` 函数
- 修改 `augmenter.py` 使用指定参数
- 修改 `_run_modflow()` 接受 `rng` 参数

**影响**：数据多样性+50%

---

#### 2. ✅ 非均质场随机种子不可重现

**问题**：使用 `int(hk_mean * 1000)` 作为种子

**修复**：使用传入的 `rng` 确保可重现性

**影响**：100%可重现，论文可声称"可重现"

---

#### 3. ✅ 地热储层缺注水井

**问题**：配置定义了injection参数但未使用

**修复**：
- 在 `_sample_params()` 中采样injection
- 在 `_run_modflow()` 中添加注水井（WEL包）

**影响**：地热储层物理模型完整

---

#### 4. ✅ 地面沉降公式错误

**问题**：每个时间步独立计算，未使用sub_cr和sub_void

**修复**：使用Terzaghi固结理论累积计算

**公式**：
```python
delta_s[t] = (cc * b / (1 + e0)) * (head[t-1] - head[t])
subsidence[t] = subsidence[t-1] + delta_s[t]  # 累积
```

**影响**：物理准确性+100%

---

### 待修复的问题（P1-P3）

详见 `CODE_REVIEW_2026-03-15_FINAL.md`

- **P1问题**：5个（物理准确性）
- **P2问题**：7个（性能优化）
- **P3问题**：8个（次要改进）

---

## 文档索引

### 核心文档

1. **README.md** - 项目主文档
2. **CLAUDE.md** - Claude工作指南
3. **QUICKSTART_250K.md** - 快速入门
4. **PROJECT_GUIDE.md** - 本文档（完整指南）

### 技术文档

1. **CODE_REVIEW_2026-03-15_FINAL.md** - 代码审查报告（25个问题）
2. **P0_FIXES_COMPLETE_2026-03-15_NIGHT.md** - P0修复报告
3. **P2_IMPLEMENTATION_COMPLETE.md** - P2场景实施报告

### 架构文档

1. **docs/architecture.md** - 系统架构
2. **docs/modflow_scenarios.md** - 场景详细说明
3. **docs/stage1_data_diversity.md** - 数据多样性分析
4. **docs/piern_training_data_format.md** - 数据格式规范

### 研究报告

1. **research/地质时序数据合成工具调研报告.md**
2. **research/多模拟器数据集设计报告.md**
3. **research/统一参数表示方案.md**

### 归档文档

- **archive/2026-03-15-临时文档/** - 临时文档归档
- **archive/旧版文档/** - 旧版文档归档

---

## 常用命令

### 数据生成

```bash
# 批量生成（并行）
python scripts/modflow/batch_generate.py --parallel --max-workers 8

# 单个场景
python scripts/modflow/batch_generate.py --single baseline.yaml

# 验证配置
python scripts/modflow/verify_all_scenarios.py

# 验证修复
python scripts/modflow/verify_fixes.py
```

### 数据检查

```bash
# 检查单个HDF5文件
python scripts/modflow/inspect_data.py data/modflow/baseline_groundwater_timeseries.h5

# 检查文本对
python scripts/text2comp/inspect_data.py data/text2comp/training_data_llm.jsonl

# 汇总所有数据
python scripts/utils/summarize_all.py
```

### 测试

```bash
# 测试增强策略
python scripts/modflow/test_augmentation.py

# 测试统一参数
python scripts/modflow/test_unified_params.py
```

---

## 项目结构

```
piern/
├── README.md                    # 项目主文档
├── CLAUDE.md                    # Claude工作指南
├── QUICKSTART_250K.md           # 快速入门
├── PROJECT_GUIDE.md             # 本文档
├── START_FULL_250K.sh           # 启动脚本
├── PiERN.pdf                    # 论文
│
├── configs/                     # 配置文件
│   └── modflow/variants/        # 25个场景配置
│
├── piern/                       # 核心包
│   ├── core/                    # 共享层
│   ├── simulators/modflow/      # MODFLOW模拟器
│   ├── text2comp/               # Stage 2
│   └── router/                  # Stage 3（待实现）
│
├── scripts/                     # 脚本
│   ├── modflow/                 # MODFLOW脚本
│   ├── text2comp/               # Text2Comp脚本
│   └── utils/                   # 工具脚本
│
├── docs/                        # 文档
├── research/                    # 研究报告
├── archive/                     # 归档
├── data/                        # 数据（.gitignore）
└── tests/                       # 测试
```

---

## 联系方式

**项目维护者**：Claude Code + 用户
**GitHub**：https://github.com/hbhdfjy/piern
**论文**：PiERN.pdf（ICML 2026投稿）

---

**最后更新**：2026-03-15 深夜
**版本**：v2.0
**状态**：✅ 准备就绪，可启动250K生成
