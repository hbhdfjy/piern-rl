#!/usr/bin/env python3
"""
Stage 2 完整流程 - 一键生成

完全 LLM 生成方案（两步法）：
1. 使用 LLM 生成模板
2. 使用模板批量生成训练数据
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
import random
import time
import h5py
import yaml
from tqdm import tqdm
from data_synthesis.text_generators.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_templates_batch(
    n_templates_total: int,
    batch_size: int,
    llm_client: LLMClient,
    max_retries: int = 3,
):
    """
    分批生成模板。

    Args:
        n_templates_total: 总模板数
        batch_size: 每批生成数量
        llm_client: LLM 客户端
        max_retries: 每批最大重试次数

    Returns:
        生成的模板列表
    """

    system_prompt = """你是一个专业的地下水模拟专家和语言学家，擅长创建多样化的参数描述模板。

你的任务是创建用于描述 MODFLOW 地下水模型参数的中文模板。

参数说明：
- hk (水力传导系数): 含水层的渗透能力，单位 m/day
- sy (储水系数): 含水层释放水的能力，无量纲，范围 0-1
- pumping (抽水量): 抽水井的流量，单位 m³/day，负值表示抽水
- strt (初始水头): 模拟开始时的地下水位，单位 m
- rch (补给量): 地表降雨入渗的补给速率，单位 m/day

模板要求：
1. 必须包含所有 5 个参数的占位符：{hk}, {sy}, {pumping}, {strt}, {rch}
2. 使用多样化的表达方式（技术性、自然语言、简化等）
3. 可以变换参数顺序
4. 可以使用不同的同义词（如"渗透率"代替"水力传导系数"）
5. 可以使用不同的单位表达（如"米每天"代替"m/day"）
6. 不要使用 Markdown 或特殊符号
7. 每个模板必须是一个完整的句子或短语

输出格式：
每行一个模板，纯文本格式，不要编号或其他标记。
"""

    all_templates = []
    n_batches = (n_templates_total + batch_size - 1) // batch_size

    logger.info(f"开始分批生成模板...")
    logger.info(f"总目标: {n_templates_total} 个模板")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"总批次数: {n_batches}")

    for batch_idx in range(n_batches):
        batch_target = min(batch_size, n_templates_total - len(all_templates))

        logger.info(f"\n批次 {batch_idx + 1}/{n_batches}: 目标 {batch_target} 个模板")

        for attempt in range(max_retries):
            try:
                user_prompt = f"""请生成 {batch_target} 个不同的 MODFLOW 参数描述模板。

要求：
1. 风格多样化：包括技术性、自然语言、简化格式等多种风格
2. 参数顺序随机
3. 使用不同的同义词和单位表达
4. 每个模板都必须包含所有 5 个参数：{{hk}}, {{sy}}, {{pumping}}, {{strt}}, {{rch}}

现在请生成 {batch_target} 个新的、不同的模板：
"""

                response = llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.9,
                    max_tokens=3000,
                )

                # 解析模板
                batch_templates = []
                lines = response.strip().split('\n')

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # 移除可能的编号前缀
                    line = line.lstrip('0123456789.-) ')

                    # 验证模板是否包含所有必需的占位符
                    required = ['{hk}', '{sy}', '{pumping}', '{strt}', '{rch}']
                    if all(ph in line for ph in required):
                        batch_templates.append(line)

                logger.info(f"  尝试 {attempt + 1}: 生成了 {len(batch_templates)} 个有效模板")

                if len(batch_templates) > 0:
                    all_templates.extend(batch_templates)
                    break

            except Exception as e:
                logger.warning(f"  尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        # 如果已经达到目标，提前退出
        if len(all_templates) >= n_templates_total:
            break

        # 批次间延迟
        if batch_idx < n_batches - 1:
            time.sleep(1)

    # 去重
    unique_templates = list(set(all_templates))

    logger.info(f"\n模板生成完成:")
    logger.info(f"  生成总数: {len(all_templates)}")
    logger.info(f"  去重后: {len(unique_templates)}")
    logger.info(f"  目标: {n_templates_total}")

    return unique_templates


def load_stage1_data(data_dir: str):
    """加载 Stage 1 数据。"""
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("*_groundwater_timeseries.h5"))

    all_data = []

    logger.info("加载 Stage 1 数据...")
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

    logger.info(f"✓ 加载了 {len(all_data)} 个样本")
    return all_data


def generate_training_data(
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

    logger.info(f"\n开始生成训练数据...")
    logger.info(f"  模板数: {len(templates)}")
    logger.info(f"  样本数: {len(stage1_data)}")
    logger.info(f"  每样本变体数: {n_variants_per_sample}")
    logger.info(f"  预计总输出: {len(stage1_data) * n_variants_per_sample:,}")

    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in tqdm(stage1_data, desc="生成训练数据"):
            # 为每个样本随机选择 N 个模板
            selected_templates = random.sample(
                templates,
                min(n_variants_per_sample, len(templates))
            )

            for variant_idx, template in enumerate(selected_templates):
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

    logger.info(f"✓ 生成了 {total_pairs:,} 个训练对")
    return total_pairs


def run_complete_pipeline(config_path: str):
    """运行完整的 Stage 2 流程。"""

    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print("=" * 70)
    print("Stage 2 完整流程 - 完全 LLM 生成方案（两步法）")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print("=" * 70)
    print()

    # 显示配置
    logger.info("配置信息:")
    logger.info(f"  LLM 提供商: {config['llm']['provider']}")
    logger.info(f"  模型: {config['llm']['model']}")
    logger.info(f"  目标模板数: {config['n_templates']}")
    logger.info(f"  批次大小: {config.get('template_batch_size', 20)}")
    logger.info(f"  每样本变体数: {config['n_variants_per_sample']}")
    logger.info(f"  Stage 1 数据: {config['stage1_data_dir']}")
    logger.info(f"  输出目录: {config['output_dir']}")

    # 初始化 LLM 客户端
    logger.info("\n初始化 LLM 客户端...")
    llm_client = LLMClient(
        provider=config['llm']['provider'],
        model=config['llm']['model'],
        api_key=config['llm'].get('api_key'),
        base_url=config['llm'].get('base_url'),
        timeout=config['llm'].get('timeout', 120),
    )
    logger.info("✓ LLM 客户端初始化成功")

    # ========================================
    # 第一步：生成模板
    # ========================================
    print("\n" + "=" * 70)
    print("第一步：使用 LLM 生成模板")
    print("=" * 70)

    templates = generate_templates_batch(
        n_templates_total=config['n_templates'],
        batch_size=config.get('template_batch_size', 20),
        llm_client=llm_client,
        max_retries=3,
    )

    if len(templates) == 0:
        logger.error("✗ 未能生成任何有效模板")
        return

    # 保存模板
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    template_file = output_dir / "templates_llm_generated.json"
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump({
            'n_templates': len(templates),
            'templates': templates,
            'llm_config': {
                'provider': config['llm']['provider'],
                'model': config['llm']['model'],
            }
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✓ 模板已保存到: {template_file}")

    # 显示模板示例
    print("\n模板示例（前 10 个）:")
    print("-" * 70)
    for i, template in enumerate(templates[:10], 1):
        print(f"{i}. {template}")
    if len(templates) > 10:
        print(f"... 还有 {len(templates) - 10} 个模板")

    # ========================================
    # 第二步：加载 Stage 1 数据
    # ========================================
    print("\n" + "=" * 70)
    print("第二步：加载 Stage 1 数据")
    print("=" * 70)

    stage1_data = load_stage1_data(config['stage1_data_dir'])

    # ========================================
    # 第三步：生成训练数据
    # ========================================
    print("\n" + "=" * 70)
    print("第三步：使用模板生成训练数据")
    print("=" * 70)

    output_file = output_dir / config['output_file']
    total_pairs = generate_training_data(
        templates=templates,
        stage1_data=stage1_data,
        n_variants_per_sample=config['n_variants_per_sample'],
        output_file=str(output_file),
        seed=config.get('seed', 42),
    )

    # 生成统计报告
    summary = {
        'output_file': str(output_file),
        'template_file': str(template_file),
        'total_pairs': total_pairs,
        'n_templates': len(templates),
        'n_samples': len(stage1_data),
        'n_variants_per_sample': config['n_variants_per_sample'],
        'llm_config': {
            'provider': config['llm']['provider'],
            'model': config['llm']['model'],
        },
        'seed': config.get('seed', 42),
    }

    summary_file = output_dir / f"{Path(config['output_file']).stem}_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ 统计报告已保存到: {summary_file}")

    # ========================================
    # 完成
    # ========================================
    print("\n" + "=" * 70)
    print("✓ Stage 2 完整流程完成！")
    print("=" * 70)
    print(f"生成的模板数: {len(templates)}")
    print(f"生成的训练对数: {total_pairs:,}")
    print(f"\n输出文件:")
    print(f"  模板: {template_file}")
    print(f"  训练数据: {output_file}")
    print(f"  统计报告: {summary_file}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Stage 2 完整流程 - 一键生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用默认配置
  python scripts/data_synthesis/run_stage2_complete.py

  # 使用自定义配置
  python scripts/data_synthesis/run_stage2_complete.py \\
    --config configs/data_synthesis/stage2_complete.yaml
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/data_synthesis/stage2_complete.yaml",
        help="配置文件路径",
    )

    args = parser.parse_args()

    run_complete_pipeline(args.config)


if __name__ == "__main__":
    main()
