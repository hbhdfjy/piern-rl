#!/usr/bin/env python3
"""
Text-to-Computation Stage 2 数据生成脚本。

用法：
    python scripts/text2comp/generate_stage2.py
    python scripts/text2comp/generate_stage2.py --config configs/text2comp/default.yaml
"""

import sys
import os

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from piern.text2comp.pipeline import main

if __name__ == "__main__":
    main()
