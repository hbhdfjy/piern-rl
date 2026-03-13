"""
Stage 2: Text-to-Computation 训练数据生成。

使用完全 LLM 生成方案（零模板依赖）。
"""

from piern.text2comp.generator import LLMTextGenerator
from piern.text2comp.pipeline import run_llm_pipeline

__all__ = [
    "LLMTextGenerator",
    "run_llm_pipeline",
]
