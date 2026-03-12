"""
PDEBench 任务 RL 训练脚本。

任务描述：
    - 专家：3 个 FNO 模型（每个 PDE 一个）
    - 奖励：RMSE vs 真值
    - 数据路径：data/pdebench/

用法：
    python scripts/rl_training/train_pdebench.py
    python scripts/rl_training/train_pdebench.py --config configs/rl_training/pdebench.yaml

TODO:
    - 实现 PDEBench 环境初始化
    - 加载 Stage 3 检查点作为初始化
    - 配置 GRPO 超参数
    - 启动训练循环并记录 wandb 指标
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    parser = argparse.ArgumentParser(description="PDEBench 任务 RL 训练（GRPO）")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/rl_training/pdebench.yaml",
        help="YAML 配置文件路径",
    )
    args = parser.parse_args()

    # TODO: 从 rl_training.trainer 导入并启动训练
    raise NotImplementedError("PDEBench RL 训练脚本尚未实现，请参考 rl_training/ 子项目")


if __name__ == "__main__":
    main()
