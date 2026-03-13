"""
基于 LLM 的文本生成器。

完全使用 LLM 生成参数描述，不依赖固定模板。
"""

import logging
import random
from typing import Dict, List, Optional
import json

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMTextGenerator:
    """使用 LLM 生成参数描述文本。"""

    def __init__(
        self,
        llm_client: LLMClient,
        temperature: float = 0.8,
        max_tokens: int = 200,
        style_diversity: bool = True,
    ):
        """
        初始化 LLM 文本生成器。

        Args:
            llm_client: LLM 客户端
            temperature: 温度参数（越高越随机）
            max_tokens: 最大生成 token 数
            style_diversity: 是否使用多样化的风格提示
        """
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.style_diversity = style_diversity

        # 系统提示词
        self.system_prompt = """你是一个专业的地下水模拟专家，擅长用自然语言描述 MODFLOW 地下水模型的参数配置。

你的任务是将数值参数转化为清晰、准确的中文描述。

参数说明：
- hk (水力传导系数): 含水层的渗透能力，单位 m/day（米/天）
- sy (储水系数): 含水层释放水的能力，无量纲，范围 0-1
- pumping (抽水量): 抽水井的流量，单位 m³/day（立方米/天），负值表示抽水
- strt (初始水头): 模拟开始时的地下水位，单位 m（米）
- rch (补给量): 地表降雨入渗的补给速率，单位 m/day（米/天）

要求：
1. 必须包含所有 5 个参数的数值
2. 使用专业但易懂的语言
3. 可以使用同义词（如"渗透率"代替"水力传导系数"）
4. 可以变换单位表达（如"米每天"代替"m/day"）
5. 不要添加任何解释性文字，只输出参数描述
6. 不要使用 Markdown 格式或特殊符号
"""

        # 风格提示词（用于增加多样性）
        self.style_prompts = [
            "使用技术性的、简洁的描述方式",
            "使用自然流畅的叙述方式",
            "使用类似学术论文的正式表达",
            "使用工程报告的专业风格",
            "使用简化的、紧凑的格式（如 K=值, Sy=值）",
            "使用带有单位的完整表达",
            "按照：水力传导系数、储水系数、抽水量、初始水头、补给量的顺序",
            "随机调整参数的描述顺序",
            "强调物理含义（如'含水层渗透性'而非'K值'）",
            "使用数学符号表示（如 K、Sy、Q、H₀、R）",
        ]

    def generate_text(
        self,
        params: Dict[str, float],
        scenario: Optional[str] = None,
    ) -> str:
        """
        使用 LLM 生成参数描述文本。

        Args:
            params: 参数字典，如 {"hk": 13.76, "sy": 0.131, ...}
            scenario: 场景描述（可选），如 "Baseline", "High Permeability"

        Returns:
            生成的文本描述
        """
        # 构建用户提示词
        prompt = self._build_prompt(params, scenario)

        # 调用 LLM 生成
        text = self.llm_client.generate(
            prompt=prompt,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # 后处理：清理多余的空白和换行
        text = " ".join(text.split())

        return text

    def _build_prompt(
        self,
        params: Dict[str, float],
        scenario: Optional[str] = None,
    ) -> str:
        """构建用户提示词。"""
        # 基础提示
        prompt_parts = []

        # 添加场景信息（如果有）
        if scenario:
            prompt_parts.append(f"场景：{scenario}")

        # 添加参数信息
        prompt_parts.append("请描述以下 MODFLOW 地下水模型参数：")
        prompt_parts.append(f"- 水力传导系数 (hk): {params['hk']:.4f} m/day")
        prompt_parts.append(f"- 储水系数 (sy): {params['sy']:.4f}")
        prompt_parts.append(f"- 抽水量 (pumping): {params['pumping']:.4f} m³/day")
        prompt_parts.append(f"- 初始水头 (strt): {params['strt']:.4f} m")
        prompt_parts.append(f"- 补给量 (rch): {params['rch']:.6f} m/day")

        # 添加风格提示（随机选择）
        if self.style_diversity:
            style = random.choice(self.style_prompts)
            prompt_parts.append(f"\n风格要求：{style}")

        return "\n".join(prompt_parts)

    def generate_batch(
        self,
        params_list: List[Dict[str, float]],
        scenarios: Optional[List[str]] = None,
        show_progress: bool = True,
    ) -> List[str]:
        """
        批量生成文本。

        Args:
            params_list: 参数字典列表
            scenarios: 场景描述列表（可选）
            show_progress: 是否显示进度条

        Returns:
            生成的文本列表
        """
        if scenarios is None:
            scenarios = [None] * len(params_list)

        if show_progress:
            from tqdm import tqdm
            iterator = tqdm(
                zip(params_list, scenarios),
                total=len(params_list),
                desc="LLM 生成文本",
            )
        else:
            iterator = zip(params_list, scenarios)

        results = []
        for params, scenario in iterator:
            try:
                text = self.generate_text(params, scenario)
                results.append(text)
            except Exception as e:
                logger.error(f"生成文本失败: {e}")
                # 使用简单的后备方案
                fallback_text = self._generate_fallback_text(params)
                results.append(fallback_text)
                logger.warning(f"使用后备文本: {fallback_text}")

        return results

    def _generate_fallback_text(self, params: Dict[str, float]) -> str:
        """当 LLM 失败时的后备方案。"""
        return (
            f"hk={params['hk']:.4f} m/day, "
            f"sy={params['sy']:.4f}, "
            f"pumping={params['pumping']:.4f} m³/day, "
            f"strt={params['strt']:.4f} m, "
            f"rch={params['rch']:.6f} m/day"
        )

    def validate_generated_text(
        self,
        text: str,
        params: Dict[str, float],
        tolerance: float = 0.01,
    ) -> bool:
        """
        验证生成的文本是否包含正确的参数值。

        Args:
            text: 生成的文本
            params: 原始参数
            tolerance: 数值容差（相对误差）

        Returns:
            是否验证通过
        """
        # 简单验证：检查所有参数值是否出现在文本中
        for param_name, param_value in params.items():
            # 将数值转为字符串，检查是否在文本中
            value_str = f"{param_value:.2f}"
            if value_str not in text:
                # 尝试其他格式
                value_str_alt = f"{param_value:.4f}"
                if value_str_alt not in text:
                    logger.warning(
                        f"参数 {param_name}={param_value} 未在生成文本中找到: {text}"
                    )
                    return False

        return True


def test_llm_text_generator():
    """测试 LLM 文本生成器。"""
    # 初始化 LLM 客户端
    try:
        llm_client = LLMClient(
            provider="openai",
            model="gpt-3.5-turbo",
        )
    except Exception as e:
        print(f"无法初始化 OpenAI 客户端: {e}")
        print("尝试使用 SiliconFlow...")
        llm_client = LLMClient(
            provider="siliconflow",
            model="Qwen/Qwen2.5-7B-Instruct",
        )

    # 初始化文本生成器
    generator = LLMTextGenerator(llm_client, temperature=0.8)

    # 测试单个样本
    params = {
        "hk": 13.76,
        "sy": 0.131,
        "pumping": -390.9,
        "strt": 6.92,
        "rch": 0.0014,
    }

    print("=" * 60)
    print("测试单个样本生成：")
    print("=" * 60)

    for i in range(3):
        text = generator.generate_text(params, scenario="Baseline")
        print(f"\n变体 {i+1}: {text}")

        # 验证
        is_valid = generator.validate_generated_text(text, params)
        print(f"验证结果: {'✓ 通过' if is_valid else '✗ 失败'}")

    # 测试批量生成
    print("\n" + "=" * 60)
    print("测试批量生成：")
    print("=" * 60)

    params_list = [
        {"hk": 10.0, "sy": 0.1, "pumping": -100.0, "strt": 5.0, "rch": 0.001},
        {"hk": 25.0, "sy": 0.2, "pumping": -300.0, "strt": 7.0, "rch": 0.002},
        {"hk": 40.0, "sy": 0.25, "pumping": -450.0, "strt": 8.5, "rch": 0.0015},
    ]

    texts = generator.generate_batch(params_list, show_progress=True)

    for i, (params, text) in enumerate(zip(params_list, texts)):
        print(f"\n样本 {i+1}:")
        print(f"参数: {params}")
        print(f"文本: {text}")


if __name__ == "__main__":
    test_llm_text_generator()
