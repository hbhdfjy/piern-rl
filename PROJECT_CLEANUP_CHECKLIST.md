# 项目清理检查清单

**用途**: 每次更新项目后，使用此清单清理不需要的文件

## 🔍 清理步骤

### 1. 检查根目录

```bash
ls -la | grep "\.md$"
```

**保留的文档**：
- ✅ `README.md` - 项目主文档
- ✅ `CLAUDE.md` - Claude Code 指导
- ✅ `PROJECT_SCOPE.md` - 项目范围
- ✅ `ROADMAP.md` - 路线图
- ✅ `STAGE2_COMPLETE_INTEGRATION.md` - Stage 2 整合说明
- ✅ `STAGE2_USAGE.md` - Stage 2 使用指南
- ✅ `CLEANUP_REPORT.md` - 最新清理报告
- ✅ `PROJECT_CLEANUP_CHECKLIST.md` - 本清单

**删除的文档类型**：
- ❌ `*_PROGRESS.md` - 进度报告（临时）
- ❌ `*_STATUS.md` - 状态报告（临时）
- ❌ `*_SUMMARY.md` - 临时总结（除非是最新的）
- ❌ `TASK_*.md` - 任务记录（临时）
- ❌ `*_OLD.md` - 旧版本文档

### 2. 检查 scripts/data_synthesis/

```bash
ls -la scripts/data_synthesis/*.py
```

**保留的脚本**：
- ✅ `run_stage2_complete.py` - Stage 2 主脚本（最新）
- ✅ `test_stage2_complete.py` - Stage 2 测试
- ✅ `generate_templates_with_llm.py` - 模板生成
- ✅ `generate_data_with_templates.py` - 数据生成
- ✅ `batch_generate_modflow.py` - Stage 1 批量生成
- ✅ `generate_modflow_configs.py` - 配置生成
- ✅ `run_modflow.py` - MODFLOW 运行
- ✅ `inspect_*.py` - 检查工具
- ✅ `summarize_*.py` - 汇总工具

**删除的脚本类型**：
- ❌ `*_old.py` - 旧版本脚本
- ❌ `*_test.py` - 临时测试脚本（除非是正式测试）
- ❌ `quick_*.py` - 快速测试脚本（临时）
- ❌ `tmp_*.py` - 临时脚本
- ❌ `debug_*.py` - 调试脚本（临时）

### 3. 检查 configs/data_synthesis/

```bash
ls -la configs/data_synthesis/*.yaml
```

**保留的配置**：
- ✅ `modflow.yaml` - Stage 1 配置
- ✅ `stage2_complete.yaml` - Stage 2 配置（最新）
- ✅ `modflow_variants/` - 场景变体配置

**删除的配置类型**：
- ❌ `*_old.yaml` - 旧版本配置
- ❌ `*_test.yaml` - 测试配置（临时）
- ❌ `*_backup.yaml` - 备份配置（临时）

### 4. 检查 data/text2comp/

```bash
ls -la data/text2comp/
```

**保留的数据**：
- ✅ `templates_llm_final.json` - 最终模板
- ✅ `training_data_from_llm_templates.jsonl` - 训练数据
- ✅ `training_data_from_llm_templates_summary.json` - 统计报告
- ✅ `training_data_stage2_complete.jsonl` - Stage 2 完整数据（如果生成了）
- ✅ `templates_llm_generated.json` - 生成的模板（如果生成了）

**删除的数据类型**：
- ❌ `*_batch_*.json` - 批次数据（临时）
- ❌ `*_progress.json` - 进度数据（临时）
- ❌ `*_test.jsonl` - 测试数据（临时）
- ❌ `*_old.jsonl` - 旧版本数据
- ❌ `data/text2comp/test/` - 测试输出目录

### 5. 检查系统文件

```bash
find . -name ".DS_Store" -o -name "*.tmp" -o -name "*.bak" -o -name "*~"
```

**删除所有系统临时文件**：
```bash
find . -name ".DS_Store" -type f -delete
find . -name "*.tmp" -type f -delete
find . -name "*.bak" -type f -delete
find . -name "*~" -type f -delete
```

### 6. 检查 docs/

```bash
ls -la docs/*.md
```

**保留的文档**：
- ✅ `data_synthesis_overview.md` - 数据合成概述
- ✅ `modflow_stage1_detailed.md` - Stage 1 详细说明
- ✅ `stage1_data_diversity.md` - Stage 1 多样性分析
- ✅ `piern_training_data_format.md` - 数据格式说明
- ✅ `地质时序数据合成工具调研报告.md` - 调研报告

**删除的文档类型**：
- ❌ `*_old.md` - 旧版本文档
- ❌ `QUICK_START_*.md` - 快速开始（如果已被新文档替代）
- ❌ `*_draft.md` - 草稿文档

## 🤖 自动清理脚本

创建 `scripts/cleanup.sh`：

```bash
#!/bin/bash
# 自动清理脚本

echo "======================================================================"
echo "项目清理"
echo "======================================================================"
echo ""

# 1. 删除系统文件
echo "1. 删除系统临时文件..."
find . -name ".DS_Store" -type f -delete
find . -name "*.tmp" -type f -delete
find . -name "*.bak" -type f -delete
find . -name "*~" -type f -delete
echo "   ✓ 完成"

# 2. 删除测试输出
echo "2. 删除测试输出..."
rm -rf data/text2comp/test/
echo "   ✓ 完成"

# 3. 删除临时批次数据
echo "3. 删除临时批次数据..."
rm -f data/text2comp/*_batch_*.json
rm -f data/text2comp/*_progress.json
echo "   ✓ 完成"

# 4. 删除 Python 缓存
echo "4. 删除 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
echo "   ✓ 完成"

echo ""
echo "======================================================================"
echo "✓ 清理完成！"
echo "======================================================================"
```

使用方式：
```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh
```

## 📋 清理原则

1. **保留核心功能文件** - 项目运行必需的脚本、配置、数据
2. **保留最新文档** - 最新的使用指南、说明、报告
3. **删除过时文件** - 被新文件替代的旧版本
4. **删除临时文件** - 测试、调试、开发过程中产生的临时文件
5. **删除重复内容** - 功能重复的脚本、配置、文档

## ⚠️ 注意事项

### 删除前确认

对于以下文件，删除前务必确认：
- 数据文件（`.jsonl`, `.h5`）- 确认是否有备份
- 配置文件（`.yaml`）- 确认是否还在使用
- 脚本文件（`.py`）- 确认是否被其他脚本依赖

### 安全删除命令

使用 `-i` 参数进行交互式删除：
```bash
rm -i file.txt  # 删除前会询问
```

或先移动到临时目录：
```bash
mkdir -p /tmp/piern_cleanup
mv file.txt /tmp/piern_cleanup/  # 移动而不是删除
```

## 📊 清理检查表

每次更新项目后，使用此检查表：

- [ ] 检查根目录，删除临时文档
- [ ] 检查 scripts/，删除临时脚本
- [ ] 检查 configs/，删除旧配置
- [ ] 检查 data/text2comp/，删除临时数据
- [ ] 删除所有 .DS_Store 文件
- [ ] 删除所有 Python 缓存
- [ ] 更新 .gitignore（如有新的忽略规则）
- [ ] 生成清理报告（可选）

## 🎯 最佳实践

### 1. 使用版本号

对于重要文件，使用版本号而不是 `_old`：
```
config_v1.yaml
config_v2.yaml
config_v3.yaml (当前)
```

### 2. 使用日期标记

对于临时文件，使用日期标记：
```
test_2026-03-13.py
debug_2026-03-13.log
```

### 3. 定期清理

建议清理频率：
- 每次重大更新后：立即清理
- 每周：快速检查
- 每月：全面清理

### 4. 保留清理记录

每次清理后更新 `CLEANUP_REPORT.md`，记录：
- 删除的文件列表
- 删除原因
- 清理日期

## 📚 相关文档

- `CLEANUP_REPORT.md` - 最新清理报告
- `.gitignore` - Git 忽略规则
- `STAGE2_COMPLETE_INTEGRATION.md` - 项目整合说明

---

**记住：每次更新项目后都要执行清理！保持项目整洁！** 🧹
