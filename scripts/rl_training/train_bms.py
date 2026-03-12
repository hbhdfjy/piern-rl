"""
BMS（电池管理系统）任务 RL 训练脚本。

任务描述：
    - 专家：SoH 神经网络 + 线性利润公式
    - 奖励：R = Δp·P - α·c_a·1200
    - 调用链：两步（SoH → 利润），适合验证 RL 流程

用法：
    python scripts/rl_training/train_bms.py
    python scripts/rl_training/train_bms.py --config configs/rl_training/bms.yaml

TODO:
    - 实现 BMS 环境初始化
    - 加载 Stage 3 检查点作为初始化
    - 配置 GRPO 超参数
    - 启动训练循环并记录 wandb 指标
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    parser = argparse.ArgumentParser(description="BMS 任务 RL 训练（GRPO）")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/rl_training/bms.yaml",
        help="YAML 配置文件路径",
    )
    args = parser.parse_args()

    # TODO: 从 rl_training.trainer 导入并启动训练
    raise NotImplementedError("BMS RL 训练脚本尚未实现，请参考 rl_training/ 子项目")


if __name__ == "__main__":
    main()
