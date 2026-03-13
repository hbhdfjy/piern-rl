#!/usr/bin/env python3
"""
使用 LLM 生成模板。

完全 LLM 生成方案 - 第一步：生成模板库
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
from data_synthesis.text_generators.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_templates(
    n_templates: int,
    llm_client: LLMClient,
    output_file: str,
):
    """
    使用 LLM 生成模板。

    Args:
        n_templates: 要生成的模板数量
        llm_client: LLM 客户端
        output_file: 输出文件路径
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

    user_prompt = f"""请生成 {n_templates} 个不同的 MODFLOW 参数描述模板。

要求：
1. 风格多样化：包括技术性、自然语言、简化格式等多种风格
2. 参数顺序随机
3. 使用不同的同义词和单位表达
4. 每个模板都必须包含所有 5 个参数：{{hk}}, {{sy}}, {{pumping}}, {{strt}}, {{rch}}

示例（不要重复这些）：
- hk={{hk}} m/day, sy={{sy}}, pumping={{pumping}} m³/day, strt={{strt}} m, rch={{rch}} m/day
- 含水层渗透系数为 {{hk}} 米每天，储水系数为 {{sy}}，抽水量为 {{pumping}} 立方米每天，初始水头为 {{strt}} 米，补给量为 {{rch}} 米每天
- 水力传导系数：{{hk}} m/d，给水度：{{sy}}，井流量：{{pumping}} m³/d，初始水位：{{strt}} m，入渗率：{{rch}} m/d

现在请生成 {n_templates} 个新的、不同的模板：
"""

    logger.info(f"开始生成 {n_templates} 个模板...")
    logger.info(f"LLM: {llm_client.provider} - {llm_client.model}")

    try:
        response = llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.9,  # 高温度以增加多样性
            max_tokens=4000,  # 足够生成所有模板
        )

        # 解析模板
        templates = []
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            # 跳过空行和编号
            if not line or line[0].isdigit():
                continue
            # 移除可能的编号前缀（如 "1. ", "1) ", "- "）
            line = line.lstrip('0123456789.-) ')

            # 验证模板是否包含所有必需的占位符
            required_placeholders = ['{hk}', '{sy}', '{pumping}', '{strt}', '{rch}']
            if all(ph in line for ph in required_placeholders):
                templates.append(line)

        logger.info(f"成功生成 {len(templates)} 个有效模板")

        if len(templates) < n_templates * 0.8:
            logger.warning(f"生成的有效模板数量 ({len(templates)}) 少于预期 ({n_templates})")
            logger.warning("可能需要重新生成或调整提示词")

        # 保存模板
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'n_templates': len(templates),
                'templates': templates,
                'llm_config': {
                    'provider': llm_client.provider,
                    'model': llm_client.model,
                    'temperature': 0.9,
                }
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"模板已保存到: {output_path}")

        # 显示前 5 个模板作为示例
        print("\n" + "="*70)
        print(f"生成的模板示例（前 5 个）：")
        print("="*70)
        for i, template in enumerate(templates[:5], 1):
            print(f"\n{i}. {template}")

        if len(templates) > 5:
            print(f"\n... 还有 {len(templates) - 5} 个模板")

        print("\n" + "="*70)
        print(f"✓ 总共生成 {len(templates)} 个模板")
        print(f"✓ 已保存到: {output_path}")
        print("="*70)

        return templates

    except Exception as e:
        logger.error(f"生成模板失败: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="使用 LLM 生成模板"
    )

    parser.add_argument(
        "--n-templates",
        type=int,
        default=100,
        help="要生成的模板数量（默认 100）",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="siliconflow",
        choices=["openai", "anthropic", "siliconflow", "local"],
        help="LLM 提供商",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-7B-Instruct",
        help="模型名称",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default="sk-ofpvsbvjrryqsnedalqhkzruejsfpqleryztbqnsdpmuekwp",
        help="API 密钥",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/text2comp/templates_llm.json",
        help="输出文件路径",
    )

    args = parser.parse_args()

    # 初始化 LLM 客户端
    print("="*70)
    print("使用 LLM 生成模板")
    print("="*70)
    print(f"LLM 提供商: {args.provider}")
    print(f"模型: {args.model}")
    print(f"模板数量: {args.n_templates}")
    print(f"输出文件: {args.output}")
    print("="*70)
    print()

    llm_client = LLMClient(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        timeout=120,
    )

    # 生成模板
    templates = generate_templates(
        n_templates=args.n_templates,
        llm_client=llm_client,
        output_file=args.output,
    )

    print("\n✓ 完成！")


if __name__ == "__main__":
    main()
