#!/bin/bash
# Stage 2 完整流程 - 一键启动脚本

set -e

echo "======================================================================"
echo "Stage 2 完整流程 - 一键生成"
echo "======================================================================"
echo ""
echo "流程："
echo "  1. 使用 LLM 生成模板"
echo "  2. 加载 Stage 1 数据"
echo "  3. 使用模板批量生成训练数据"
echo ""
echo "预期："
echo "  - 100 个 LLM 生成的模板"
echo "  - 6,600 个训练数据对"
echo "  - 耗时约 1-2 分钟"
echo "  - 成本约 $0.01"
echo ""
echo "======================================================================"
echo ""

# 检查 Stage 1 数据
if [ ! -d "data/modflow" ] || [ -z "$(ls -A data/modflow/*_groundwater_timeseries.h5 2>/dev/null)" ]; then
    echo "⚠️  未找到 Stage 1 数据"
    echo ""
    echo "请先运行 Stage 1 数据生成："
    echo "  python scripts/data_synthesis/run_modflow_synthesis.py"
    echo ""
    exit 1
fi

echo "✓ Stage 1 数据已准备好"
echo ""

# 询问是否继续
read -p "是否继续？[Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "======================================================================"
echo "开始生成..."
echo "======================================================================"
echo ""

# 运行主脚本
python scripts/data_synthesis/run_stage2_complete.py

echo ""
echo "======================================================================"
echo "✓ 完成！"
echo "======================================================================"
echo ""
echo "输出文件："
echo "  - data/text2comp/templates_llm_generated.json"
echo "  - data/text2comp/training_data_stage2_complete.jsonl"
echo "  - data/text2comp/training_data_stage2_complete_summary.json"
echo ""
echo "查看结果："
echo "  wc -l data/text2comp/training_data_stage2_complete.jsonl"
echo "  cat data/text2comp/training_data_stage2_complete_summary.json | python -m json.tool"
echo ""
echo "======================================================================"
