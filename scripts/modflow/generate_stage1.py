#!/usr/bin/env python3
"""
MODFLOW Stage 1 数据生成脚本。

用法：
    python scripts/modflow/generate_stage1.py
    python scripts/modflow/generate_stage1.py --config configs/modflow/default.yaml
"""

import sys
import os

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from piern.simulators.modflow.pipeline import main

if __name__ == "__main__":
    main()
