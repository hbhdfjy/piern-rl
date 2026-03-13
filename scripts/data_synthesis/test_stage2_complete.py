#!/usr/bin/env python3
"""
快速测试 Stage 2 完整流程。

生成少量数据以验证流程是否正常。
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import tempfile
import shutil

# 创建临时配置
test_config = """
llm:
  provider: siliconflow
  model: "Qwen/Qwen2.5-7B-Instruct"
  api_key: "sk-ofpvsbvjrryqsnedalqhkzruejsfpqleryztbqnsdpmuekwp"
  base_url: "https://api.siliconflow.cn/v1"
  timeout: 120

n_templates: 10
template_batch_size: 10
stage1_data_dir: "data/modflow"
n_variants_per_sample: 1
seed: 42
output_dir: "data/text2comp/test"
output_file: "test_training_data.jsonl"
"""

def main():
    print("=" * 70)
    print("Stage 2 完整流程 - 快速测试")
    print("=" * 70)
    print()
    print("测试配置:")
    print("  模板数: 10 个")
    print("  每样本变体: 1 个")
    print("  输出目录: data/text2comp/test/")
    print()
    print("预计耗时: < 30 秒")
    print("=" * 70)
    print()

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(test_config)
        config_file = f.name

    try:
        # 导入主函数
        from run_stage2_complete import run_complete_pipeline

        # 运行流程
        run_complete_pipeline(config_file)

        print()
        print("=" * 70)
        print("✓ 测试成功！")
        print("=" * 70)
        print()
        print("测试输出:")
        print("  data/text2comp/test/templates_llm_generated.json")
        print("  data/text2comp/test/test_training_data.jsonl")
        print("  data/text2comp/test/test_training_data_summary.json")
        print()
        print("你现在可以运行完整流程:")
        print("  python scripts/data_synthesis/run_stage2_complete.py")
        print("=" * 70)

    finally:
        # 清理临时文件
        Path(config_file).unlink()


if __name__ == "__main__":
    main()
