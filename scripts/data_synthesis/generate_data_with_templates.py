#!/usr/bin/env python3
"""
使用 LLM 生成的模板来生成训练数据。

完全 LLM 生成方案 - 第二步：使用模板生成数据
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
import random
import h5py
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_templates(template_file: str):
    """加载 LLM 生成的模板。"""
    with open(template_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['templates']


def load_stage1_data(data_dir: str):
    """加载 Stage 1 数据。"""
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("*_groundwater_timeseries.h5"))

    all_data = []

    for file in files:
        with h5py.File(file, 'r') as f:
            params_array = f['params'][:]
            param_names = [
                n.decode('utf-8') if isinstance(n, bytes) else n
                for n in f['param_names'][:]
            ]

            scenario = file.stem.replace('_groundwater_timeseries', '').replace('_', ' ').title()

            for i in range(len(params_array)):
                sample_params = {
                    name: float(params_array[i, j])
                    for j, name in enumerate(param_names)
                }
                all_data.append({
                    'params': sample_params,
                    'source_file': file.name,
                    'scenario': scenario,
                    'sample_index': i,
                })

    return all_data


def generate_data_with_templates(
    templates: list,
    stage1_data: list,
    n_variants_per_sample: int,
    output_file: str,
    seed: int = 42,
):
    """使用模板生成训练数据。"""

    random.seed(seed)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_pairs = 0

    logger.info(f"开始生成数据...")
    logger.info(f"模板数: {len(templates)}")
    logger.info(f"样本数: {len(stage1_data)}")
    logger.info(f"每样本变体数: {n_variants_per_sample}")
    logger.info(f"预计总输出: {len(stage1_data) * n_variants_per_sample:,}")

    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in tqdm(stage1_data, desc="生成数据"):
            # 为每个样本随机选择 N 个模板
            selected_templates = random.sample(
                templates,
                min(n_variants_per_sample, len(templates))
            )

            for variant_idx, template in enumerate(selected_templates):
                # 填充模板
                try:
                    text = template.format(**sample['params'])

                    record = {
                        'text': text,
                        'params': sample['params'],
                        'source_file': sample['source_file'],
                        'scenario': sample['scenario'],
                        'sample_index': sample['sample_index'],
                        'variant_index': variant_idx,
                    }

                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    total_pairs += 1

                except KeyError as e:
                    logger.warning(f"模板缺少占位符 {e}，跳过")
                    continue

    logger.info(f"✓ 完成！生成 {total_pairs:,} 个训练对")

    # 生成统计报告
    summary = {
        'output_file': str(output_path),
        'total_pairs': total_pairs,
        'n_templates': len(templates),
        'n_samples': len(stage1_data),
        'n_variants_per_sample': n_variants_per_sample,
        'seed': seed,
    }

    summary_file = output_path.parent / f"{output_path.stem}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ 统计报告: {summary_file}")

    return total_pairs


def main():
    parser = argparse.ArgumentParser(
        description="使用 LLM 生成的模板来生成训练数据"
    )

    parser.add_argument(
        "--templates",
        type=str,
        default="data/text2comp/templates_llm.json",
        help="模板文件路径",
    )

    parser.add_argument(
        "--stage1-dir",
        type=str,
        default="data/modflow",
        help="Stage 1 数据目录",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/text2comp/training_data_from_templates.jsonl",
        help="输出文件路径",
    )

    parser.add_argument(
        "--n-variants",
        type=int,
        default=1,
        help="每个样本使用多少个模板（默认 1）",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子",
    )

    args = parser.parse_args()

    print("="*70)
    print("使用 LLM 生成的模板生成训练数据")
    print("="*70)
    print(f"模板文件: {args.templates}")
    print(f"Stage 1 数据: {args.stage1_dir}")
    print(f"每样本变体数: {args.n_variants}")
    print(f"输出文件: {args.output}")
    print("="*70)
    print()

    # 加载模板
    logger.info("加载模板...")
    templates = load_templates(args.templates)
    logger.info(f"✓ 加载了 {len(templates)} 个模板")

    # 加载 Stage 1 数据
    logger.info("加载 Stage 1 数据...")
    stage1_data = load_stage1_data(args.stage1_dir)
    logger.info(f"✓ 加载了 {len(stage1_data)} 个样本")

    # 生成数据
    total_pairs = generate_data_with_templates(
        templates=templates,
        stage1_data=stage1_data,
        n_variants_per_sample=args.n_variants,
        output_file=args.output,
        seed=args.seed,
    )

    print()
    print("="*70)
    print("✓ 完成！")
    print("="*70)
    print(f"生成的训练对数: {total_pairs:,}")
    print(f"输出文件: {args.output}")
    print("="*70)


if __name__ == "__main__":
    main()
