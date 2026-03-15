#!/bin/bash
# 启动完整250K样本生成
# 25个场景 × 10,000样本 = 250,000样本

set -e

echo "======================================================================="
echo "开始生成完整250K MODFLOW样本"
echo "======================================================================="
echo ""
echo "配置信息："
echo "  - 场景数: 25个"
echo "  - 每场景样本数: 10,000"
echo "  - 总样本数: 250,000"
echo "  - 并行度: 8核"
echo "  - 预计时间: 20-30小时"
echo ""

# 创建必要目录
echo "[Step 1/4] 创建目录..."
mkdir -p logs data/modflow

# 测试单个场景（快速验证）
echo ""
echo "[Step 2/4] 测试baseline场景（100样本，验证代码）..."
python3 << 'EOF'
import yaml
import sys
from pathlib import Path

# 临时修改baseline配置为100样本
config_path = Path("configs/modflow/variants/baseline.yaml")
with open(config_path) as f:
    cfg = yaml.safe_load(f)

original_n_samples = cfg["n_samples"]
cfg["n_samples"] = 100

# 保存临时配置
test_config_path = Path("configs/modflow/test_baseline.yaml")
with open(test_config_path, "w") as f:
    yaml.dump(cfg, f)

print(f"创建测试配置: {test_config_path}")
print(f"样本数: {original_n_samples} -> 100")
EOF

# 运行测试
python -m piern.simulators.modflow.pipeline \
    --config configs/modflow/test_baseline.yaml

if [ $? -ne 0 ]; then
    echo ""
    echo "✗ 测试失败！请检查错误信息"
    exit 1
fi

echo ""
echo "✓ 测试成功！代码工作正常"
echo ""

# 询问确认
echo "[Step 3/4] 准备启动完整生成..."
echo ""
echo "即将生成25个场景，共250,000样本"
echo "预计耗时: 20-30小时"
echo ""
read -p "确认启动？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "取消生成"
    exit 0
fi

# 启动批量生成
echo ""
echo "[Step 4/4] 启动批量生成（后台运行）..."
echo ""

nohup python scripts/modflow/batch_generate.py \
    --skip-existing \
    --parallel \
    --max-workers 8 \
    > logs/generation_250k.log 2>&1 &

PID=$!
echo $PID > logs/generation.pid

echo "✓ 批量生成已启动！"
echo ""
echo "进程ID: $PID"
echo "日志文件: logs/generation_250k.log"
echo ""
echo "监控命令："
echo "  - 查看日志: tail -f logs/generation_250k.log"
echo "  - 查看进度: watch -n 60 'ls data/modflow/*.h5 | wc -l'"
echo "  - 查看存储: du -sh data/modflow/"
echo "  - 停止生成: kill $PID"
echo ""
echo "======================================================================="
echo "生成已在后台运行，预计20-30小时完成"
echo "======================================================================="
