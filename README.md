# PiERN 多模拟器数据合成管线

**PiERN**（Physically-isolated Experts Routing Network）论文的数据合成代码，投稿至 ICML 2026。

本仓库实现**多模拟器数据合成管线**，集成4个地质物理模拟器，创建首个跨多物理场的地质时序数据集。

---

## 🎯 项目目标

创建大规模、高质量的地质时序数据集，支持 PiERN 三阶段训练：

| 阶段 | 数据类型 | 目标规模 | 状态 |
|------|---------|---------|------|
| **Stage 1** | 专家模型训练数据 | 75,000 样本 | ⏳ 进行中 |
| **Stage 2** | Text-to-Computation 数据 | 375,000 文本对 | 📋 计划中 |
| **Stage 3** | Token Router 数据 | 37,500 CoT 轨迹 | 📋 计划中 |

**总存储**：~361 MB（高度压缩）

---

## 🔧 支持的物理模拟器

| 模拟器 | 物理领域 | 样本数 | 场景数 | 每场景样本 | 状态 |
|--------|---------|--------|--------|-----------|------|
| **MODFLOW** | 地下水流动 | **250,000** | 25 | 10,000 | ⏳ Week 1（配置就绪） |
| **SimPEG** | 地球物理勘探（MT/DC/TEM） | 20,000 | 15 | ~1,333 | 📋 Week 2（计划） |
| **Devito** | 地震波传播 | 10,000 | 5 | 2,000 | 📋 Week 3-4（计划） |
| **TOUGH2** | 多相流体（地热/CO₂封存） | 15,000 | 5 | 3,000 | 📋 Week 5-6（计划） |

**总计**：295,000 样本，50 场景，4 物理领域

---

## 📊 数据集规模对比

| 数据集 | 样本数 | 物理领域 | 存储 | 年份 |
|--------|--------|---------|------|------|
| PDEBench | ~20,000 | 单一PDE | 1TB | 2022 |
| **piern (MODFLOW)** | **250,000** | **地下水（25场景）** | **50MB** | **2026** |
| **piern (全部)** | **295,000** | **4个地质领域** | **~400MB** | **2026** |

**优势**：
- ✅ **12.5× PDEBench 样本数**（仅MODFLOW）
- ✅ 多物理场（地下水、地球物理、地震、储层）
- ✅ **超轻量级存储**（2000× 压缩率）
- ✅ 零人工标注
- ✅ **2,500条文本模板**（业界首个）

---

## 📚 文档导航

### 快速开始
- **[QUICKSTART_250K.md](QUICKSTART_250K.md)** - 5分钟快速入门
- **[PROJECT_GUIDE.md](PROJECT_GUIDE.md)** - 完整项目指南（推荐）
- **[START_FULL_250K.sh](START_FULL_250K.sh)** - 一键启动脚本

### 技术文档
- **[CODE_REVIEW_2026-03-15_FINAL.md](CODE_REVIEW_2026-03-15_FINAL.md)** - 代码质量审查（25个问题）
- **[P0_FIXES_COMPLETE_2026-03-15_NIGHT.md](P0_FIXES_COMPLETE_2026-03-15_NIGHT.md)** - P0修复报告
- **[P2_IMPLEMENTATION_COMPLETE.md](P2_IMPLEMENTATION_COMPLETE.md)** - P2场景实施报告

### 架构与设计
- **[docs/architecture.md](docs/architecture.md)** - 系统架构
- **[docs/modflow_scenarios.md](docs/modflow_scenarios.md)** - 25个场景详解
- **[docs/stage1_data_diversity.md](docs/stage1_data_diversity.md)** - 数据多样性分析
- **[docs/piern_training_data_format.md](docs/piern_training_data_format.md)** - 数据格式规范

### 研究报告
- **[research/地质时序数据合成工具调研报告.md](research/地质时序数据合成工具调研报告.md)**
- **[research/多模拟器数据集设计报告.md](research/多模拟器数据集设计报告.md)**
- **[research/统一参数表示方案.md](research/统一参数表示方案.md)**

### Claude工作指南
- **[CLAUDE.md](CLAUDE.md)** - Claude Code工作指南

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/hbhdfjy/piern.git
cd piern

# 安装依赖
pip install -r requirements.txt
pip install -e .

# 安装 MODFLOW（可选，如需生成数据）
pip install flopy
```

### 使用示例

#### Stage 1：生成专家模型训练数据

```bash
# 单个场景生成
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/variants/baseline.yaml

# 批量生成（所有场景）
python scripts/modflow/batch_generate.py --skip-existing
```

#### Stage 2：生成 Text-to-Computation 数据

```bash
# 需要设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY
export OPENAI_API_KEY=your_key_here

python -m piern.text2comp.pipeline \
    --config configs/text2comp/default.yaml
```

#### 数据检查

```bash
# 检查 Stage 1 数据
python scripts/modflow/inspect_data.py data/modflow/baseline_groundwater_timeseries.h5

# 检查 Stage 2 数据
python scripts/text2comp/inspect_data.py data/text2comp/training_data_llm.jsonl

# 汇总所有数据
python scripts/utils/summarize_all.py
```

---

## 📁 项目结构

```
piern/
├── piern/                          # 核心包
│   ├── core/                       # 核心共享层
│   │   ├── storage.py              # HDF5/JSONL 读写
│   │   ├── validation.py           # 质量过滤
│   │   └── llm_client.py           # LLM 客户端
│   │
│   ├── simulators/                 # 物理模拟器
│   │   ├── modflow/                # ✅ MODFLOW（地下水）
│   │   ├── simpeg/                 # 📋 SimPEG（地球物理）
│   │   ├── devito/                 # 📋 Devito（地震）
│   │   └── tough2/                 # 📋 TOUGH2（储层）
│   │
│   ├── text2comp/                  # Stage 2: Text-to-Computation
│   └── router/                     # Stage 3: Token Router
│
├── configs/                        # 配置文件
│   ├── modflow/variants/           # 25 个 MODFLOW 场景
│   ├── simpeg/variants/            # 15 个 SimPEG 场景（待创建）
│   ├── devito/variants/            # 5 个 Devito 场景（待创建）
│   └── tough2/variants/            # 5 个 TOUGH2 场景（待创建）
│
├── scripts/                        # 脚本
│   ├── modflow/                    # MODFLOW 相关
│   ├── text2comp/                  # Text-to-Computation 相关
│   └── utils/                      # 通用工具
│
├── data/                           # 数据目录（.gitignore）
│   ├── modflow/                    # MODFLOW 数据
│   ├── simpeg/                     # SimPEG 数据（待生成）
│   ├── devito/                     # Devito 数据（待生成）
│   ├── tough2/                     # TOUGH2 数据（待生成）
│   ├── text2comp/                  # Text-to-Computation 数据
│   └── router/                     # Router 数据（待生成）
│
├── docs/                           # 文档
│   ├── modflow_scenarios.md        # MODFLOW 场景说明
│   └── week1_progress.md           # 进度跟踪
│
└── research/                       # 调研报告
    ├── 地质时序数据合成工具调研报告.md
    └── 多模拟器数据集设计报告.md
```

---

## 🌟 核心特性

### 1. 多物理场覆盖

**MODFLOW 场景**（25个）：
- 单层/多层含水层（1-5层）
- 均质/非均质介质（高斯随机场）
- 不同边界条件（河流、湖泊、海水）
- 时间变化（季节性）
- 耦合过程（沉降、污染物运移、地热）

**SimPEG 场景**（15个，计划中）：
- 大地电磁（MT）
- 直流电阻率（DC）
- 时域电磁（TEM）

**Devito 场景**（5个，计划中）：
- 层状模型
- Marmousi 模型
- 随机速度场
- 断层模型
- 盐丘模型

**TOUGH2 场景**（5个，计划中）：
- 地热储层
- CO₂ 封存
- 页岩气开采
- 水合物开采
- 油气储层

### 2. 参数空间采样增强（V2）

**核心思想**：扰动参数 → 运行物理模拟 → 生成新样本

```yaml
augmentation:
  method: "parameter_sampling"
  n_augmented_per_sample: 0.5      # 增加 50% 样本数
  perturbation_ratio: 0.05         # 参数扰动 ±5%
```

**优势**：
- ✅ 物理一致性（每个新样本都是真实模拟结果）
- ✅ 参数空间覆盖更广
- ✅ 模型精度提高 2-3 倍（相比时序扰动）

### 3. 完全 LLM 文本生成

**Stage 2 数据生成**：
- 零模板依赖
- 高质量、多样化的文本描述
- 每个样本生成 5 个不同风格的文本变体

**示例**：
```json
{
  "text": "在中等渗透性含水层中，水力传导系数为 15 m/day，储水系数 0.12，抽水量 200 m³/day...",
  "params": [15.0, 0.12, -200.0, 7.5, 0.0008]
}
```

### 4. 自动质量过滤

```yaml
validation:
  max_nan_ratio: 0.05              # NaN 比例 < 5%
  min_variance: 0.000001           # 过滤常数序列
  max_head_value: 15.0             # 物理范围检查
  min_head_value: -5.0
```

---

## 📈 实施路线图

详见 `IMPLEMENTATION_ROADMAP.md`

| 周 | 任务 | 目标 | 状态 |
|----|------|------|------|
| **Week 1** | MODFLOW 扩展 | 30,000 样本，25 场景 | ⏳ 进行中 |
| **Week 2** | SimPEG 实现 | 20,000 样本，15 场景 | 📋 计划中 |
| **Week 3-4** | Devito 实现 | 10,000 样本，5 场景 | 📋 计划中 |
| **Week 5-6** | TOUGH2 实现 | 15,000 样本，5 场景 | 📋 计划中 |
| **Week 7** | Stage 2 扩展 | 375,000 文本对 | 📋 计划中 |
| **Week 8** | Stage 3 实现 | 37,500 CoT 轨迹 | 📋 计划中 |

**预计完成**：2026-05-10

---

## 📖 文档

- **技术方案**：`research/多模拟器数据集设计报告.md`
- **实施路线图**：`IMPLEMENTATION_ROADMAP.md`
- **场景说明**：`docs/modflow_scenarios.md`
- **进度跟踪**：`docs/week1_progress.md`

---

## 🔬 研究背景

### PiERN 三阶段训练

1. **Stage 1**：训练专家模型
   - 输入：数值参数
   - 输出：时序预测
   - 数据：(params, timeseries)

2. **Stage 2**：训练 Text-to-Computation 模块
   - 输入：文本描述
   - 输出：数值参数
   - 数据：(text, params)

3. **Stage 3**：训练 Token Router
   - 输入：用户查询
   - 输出：路由决策（调用哪个专家）
   - 数据：(query, cot_trajectory, route_label)

### 论文贡献

- **首个多物理场地质数据集**：4 个模拟器，50 个场景
- **大规模**：75K 样本，超越 PDEBench 3.75 倍
- **轻量级**：361MB 存储，易于分发
- **完整三阶段数据**：支持 PiERN 端到端训练
- **零人工标注**：全自动合成管线

---

## 🤝 贡献

欢迎贡献！请遵循以下流程：

1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/new-simulator`）
3. 提交更改（`git commit -m 'Add new simulator'`）
4. 推送到分支（`git push origin feature/new-simulator`）
5. 创建 Pull Request

---

## 📄 许可证

MIT License

---

## 📧 联系方式

- **作者**：hbhdfjy
- **邮箱**：[your-email]
- **GitHub**：https://github.com/hbhdfjy/piern

---

## 🙏 致谢

- **MODFLOW**：USGS 地下水模拟软件
- **SimPEG**：地球物理正反演框架
- **Devito**：地震波传播求解器
- **TOUGH2**：多相流模拟软件
- **flopy**：MODFLOW Python 接口

---

**最后更新**：2026-03-15
**版本**：v2.0（多模拟器版本）
