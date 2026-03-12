"""
GCAM（全球变化评估模型）任务 RL 训练脚本。

任务描述：
    - 专家：9 个领域神经代理
    - 奖励：政策对齐分数
    - 数据路径：data/gcam/

用法：
    python scripts/rl_training/train_gcam.py
    python scripts/rl_training/train_gcam.py --config configs/rl_training/gcam.yaml

TODO:
    - 实现 GCAM 环境初始化
    - 加载 Stage 3 检查点作为初始化
    - 配置 GRPO 超参数
    - 启动训练循环并记录 wandb 指标
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    parser = argparse.ArgumentParser(description="GCAM 任务 RL 训练（GRPO）")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/rl_training/gcam.yaml",
        help="YAML 配置文件路径",
    )
    args = parser.parse_args()

    # TODO: 从 rl_training.trainer 导入并启动训练
    raise NotImplementedError("GCAM RL 训练脚本尚未实现，请参考 rl_training/ 子项目")


if __name__ == "__main__":
    main()
