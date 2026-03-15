"""
为每个场景生成100条多样化的语言模板。

使用 LLM 生成高质量、多样化的文本模板，覆盖：
- 不同的表达风格（专业术语、通俗语言、技术描述）
- 不同的句式结构（陈述句、疑问句、条件句）
- 不同的细节层次（简洁、详细、超详细）
- 不同的上下文（工程应用、科研分析、教学说明）
"""

import json
import os
from pathlib import Path
from typing import List, Dict
from piern.core.llm_client import LLMClient


class TemplateGenerator:
    """语言模板生成器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate_templates_for_scenario(
        self, scenario_name: str, scenario_description: str, n_templates: int = 100
    ) -> List[str]:
        """
        为单个场景生成 N 条语言模板。

        Args:
            scenario_name: 场景名称（如 "baseline", "multilayer_3layers"）
            scenario_description: 场景描述（用于指导 LLM 生成）
            n_templates: 要生成的模板数量

        Returns:
            模板列表
        """
        templates = []

        # 分批生成（每次生成10条，避免单次请求过长）
        batch_size = 10
        n_batches = (n_templates + batch_size - 1) // batch_size

        for batch_idx in range(n_batches):
            remaining = min(batch_size, n_templates - len(templates))

            prompt = self._create_template_generation_prompt(
                scenario_name, scenario_description, remaining, batch_idx
            )

            try:
                response = self.llm.generate(prompt)
                batch_templates = self._parse_templates_from_response(response)
                templates.extend(batch_templates[:remaining])

                print(
                    f"  批次 {batch_idx + 1}/{n_batches}: 生成 {len(batch_templates)} 条模板"
                )

            except Exception as e:
                print(f"  警告: 批次 {batch_idx + 1} 生成失败: {e}")
                continue

        print(f"  ✓ 场景 '{scenario_name}' 共生成 {len(templates)} 条模板")
        return templates

    def _create_template_generation_prompt(
        self,
        scenario_name: str,
        scenario_description: str,
        n_templates: int,
        batch_idx: int,
    ) -> str:
        """创建模板生成提示词"""

        # 根据批次索引选择不同的风格指导
        style_guides = [
            "使用专业的水文地质术语，适合工程师和科研人员",
            "使用通俗易懂的语言，适合学生和初学者",
            "使用简洁的技术描述，适合快速查询和检索",
            "使用详细的参数说明，适合精确的模拟配置",
            "使用问题导向的表达，如'如何...', '什么情况下...'",
            "使用场景导向的表达，描述具体的应用案例",
            "使用对比性的表达，与其他场景进行比较",
            "使用因果性的表达，说明参数与结果的关系",
            "使用条件性的表达，描述不同条件下的行为",
            "使用混合风格，结合多种表达方式",
        ]

        style_guide = style_guides[batch_idx % len(style_guides)]

        prompt = f"""你是一个地下水模拟专家。请为以下场景生成 {n_templates} 条不同的中文文本描述模板。

**场景名称**: {scenario_name}

**场景说明**: {scenario_description}

**风格要求**: {style_guide}

**模板要求**:
1. 每条模板应该是一个完整的句子或段落（20-80个字）
2. 必须包含参数占位符，使用双花括号格式：{{{{hk}}}}, {{{{sy}}}}, {{{{pumping}}}}, {{{{rch}}}}, {{{{strt}}}}
3. 模板之间要有明显的表达差异（不同句式、不同重点、不同细节层次）
4. 使用自然流畅的中文，避免生硬翻译
5. 适合作为训练数据的输入文本

**参数说明**:
- hk: 水平渗透系数（m/day）
- sy: 比储水率（无量纲）
- pumping: 抽水量（m³/day，负值）
- rch: 补给量（m/day）
- strt: 初始水头（m）

**输出格式**:
请直接输出 {n_templates} 条模板，每行一条，不要编号，不要额外说明。

示例（仅供参考，不要照抄）:
在渗透系数为{{{{hk}}}}米每天的含水层中，抽水量{{{{pumping}}}}立方米每天时的水位变化
含水层渗透率{{{{hk}}}} m/day，储水系数{{{{sy}}}}，抽水强度{{{{pumping}}}} m³/d的地下水动态模拟
当水力传导系数K={{{{hk}}}}，比储水率Sy={{{{sy}}}}时，抽水井周围的水位降落漏斗演化

现在请生成 {n_templates} 条新的模板："""

        return prompt

    def _parse_templates_from_response(self, response: str) -> List[str]:
        """从 LLM 响应中解析模板列表"""
        lines = response.strip().split("\n")
        templates = []

        for line in lines:
            line = line.strip()
            # 跳过空行
            if not line:
                continue
            # 跳过编号（如 "1. ", "1) ", "1、"）
            if line[0].isdigit():
                # 移除编号前缀
                line = line.split(".", 1)[-1].split(")", 1)[-1].split("、", 1)[-1].strip()

            # 检查是否包含参数占位符
            if "{{" in line and "}}" in line:
                templates.append(line)

        return templates

    def save_templates(
        self, templates_by_scenario: Dict[str, List[str]], output_path: Path
    ):
        """保存所有场景的模板到JSON文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(templates_by_scenario, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 模板已保存到: {output_path}")


def generate_scenario_descriptions() -> Dict[str, str]:
    """
    为每个场景生成描述（用于指导模板生成）。

    Returns:
        场景名称 -> 场景描述的字典
    """
    return {
        # 基础场景
        "baseline": "标准地下水流动场景，中等渗透率，中等抽水强度，用于基准对比",
        "low_permeability": "低渗透率含水层（粉砂、粘土），水位变化缓慢",
        "medium_permeability": "中等渗透率含水层（细砂），典型的地下水系统",
        "high_permeability": "高渗透率含水层（砾石、粗砂），水位响应迅速",
        # 抽水强度
        "light_pumping": "轻度抽水场景，小流量开采，水位降幅小",
        "heavy_pumping": "强抽水场景，大流量开采，水位降幅大，可能形成降落漏斗",
        "artificial_recharge": "人工回灌场景，注水补给，水位上升",
        # 时间尺度
        "short_term_daily": "短期日尺度模拟（30天），适合应急响应和短期预测",
        "medium_term_halfyear": "中期半年模拟（180天），适合季节性分析",
        "long_term_twoyears": "长期两年模拟（730天），适合长期规划和趋势分析",
        # 空间分辨率
        "coarse_grid_10x10": "粗网格模拟（10×10），快速计算，区域尺度",
        "fine_grid_40x40": "细网格模拟（40×40），高精度，局部尺度",
        # 应用场景
        "arid_region": "干旱区地下水，补给量极小，蒸发强烈",
        "humid_region": "湿润区地下水，补给量大，降雨充沛",
        "urban_water_supply": "城市供水场景，多井抽水，复杂开采模式",
        # 多物理场耦合
        "multilayer_3layers": "三层含水层系统，上中下层垂直交换，各层渗透率不同",
        "multilayer_5layers": "五层含水层系统，包含隔水层，复杂的垂向水力联系",
        "heterogeneous_field": "非均质渗透率场，空间变化的水力参数，高斯随机场",
        "river_boundary": "河流边界条件，地表水与地下水交换，恒定水头边界",
        "lake_boundary": "湖泊边界条件，大面积水体与含水层交换",
        "seasonal_variation": "季节性变化场景，雨季旱季交替，补给量周期性波动",
        "seawater_intrusion": "海水入侵场景，沿海地区，密度驱动流动，淡水咸水界面",
        "land_subsidence": "地面沉降场景，地下水开采导致地层压缩和地面下沉",
        "contaminant_transport": "污染物运移场景，污染源扩散，浓度时空演化",
        "geothermal_reservoir": "地热储层场景，温度场演化，热传导和对流",
    }


def main():
    """主函数：为所有场景生成语言模板"""
    import yaml

    # 读取 text2comp 配置
    config_path = Path(__file__).parent.parent.parent / "configs" / "text2comp" / "default.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 初始化 LLM 客户端
    llm_client = LLMClient(
        provider=config["llm"]["provider"],
        model=config["llm"]["model"],
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        base_url=config["llm"].get("base_url"),
        temperature=config["llm"].get("temperature", 0.8),
        max_tokens=config["llm"].get("max_tokens", 200),
    )

    # 初始化模板生成器
    generator = TemplateGenerator(llm_client)

    # 获取场景描述
    scenario_descriptions = generate_scenario_descriptions()

    # 为每个场景生成模板
    n_templates_per_scenario = 100
    templates_by_scenario = {}

    print("=" * 60)
    print(f"开始为 {len(scenario_descriptions)} 个场景生成语言模板")
    print(f"每个场景生成 {n_templates_per_scenario} 条模板")
    print("=" * 60)
    print()

    for scenario_name, description in scenario_descriptions.items():
        print(f"处理场景: {scenario_name}")
        templates = generator.generate_templates_for_scenario(
            scenario_name, description, n_templates_per_scenario
        )
        templates_by_scenario[scenario_name] = templates
        print()

    # 保存模板
    output_dir = Path(__file__).parent.parent.parent / "data" / "text2comp"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "scenario_templates.json"

    generator.save_templates(templates_by_scenario, output_path)

    # 统计信息
    total_templates = sum(len(templates) for templates in templates_by_scenario.values())
    print()
    print("=" * 60)
    print("模板生成完成！")
    print(f"  - 场景数: {len(templates_by_scenario)}")
    print(f"  - 总模板数: {total_templates}")
    print(f"  - 平均每场景: {total_templates / len(templates_by_scenario):.1f} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
