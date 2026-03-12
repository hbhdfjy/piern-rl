"""
MODFLOW 数据合成 CLI 入口。

用法：
    python scripts/data_synthesis/run_modflow.py
    python scripts/data_synthesis/run_modflow.py --config configs/data_synthesis/modflow.yaml
"""

import argparse
import os
import sys

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data_synthesis.pipeline.modflow_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="MODFLOW 地下水位时序数据合成管线")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/data_synthesis/modflow.yaml",
        help="YAML 配置文件路径（默认：configs/data_synthesis/modflow.yaml）",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"错误：配置文件不存在：{args.config}", file=sys.stderr)
        sys.exit(1)

    output_path = run_pipeline(args.config)
    print(f"数据集已保存至：{output_path}")


if __name__ == "__main__":
    main()
