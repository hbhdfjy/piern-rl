"""
Stage 2 Text-to-Computation 训练数据生成管线（完全 LLM 版本）。

完全使用 LLM 生成文本描述，不依赖固定模板库。
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import h5py
import yaml
from tqdm import tqdm

from piern.core.llm_client import LLMClient
from piern.text2comp.generator import LLMTextGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AdaptiveStage1Loader:
    """自适应加载 Stage 1 数据文件。"""

    def __init__(self, data_dir: str):
        """
        初始化加载器。

        Args:
            data_dir: Stage 1 数据目录
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {data_dir}")

    def discover_files(self) -> List[Path]:
        """自动发现所有 Stage 1 HDF5 文件。"""
        pattern = "*_groundwater_timeseries.h5"
        files = sorted(self.data_dir.glob(pattern))

        if not files:
            raise FileNotFoundError(
                f"在 {self.data_dir} 中未找到匹配 {pattern} 的文件"
            )

        logger.info(f"发现 {len(files)} 个 Stage 1 数据文件")
        return files

    def load_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        加载文件元数据（不加载大数组）。

        Args:
            file_path: HDF5 文件路径

        Returns:
            元数据字典
        """
        with h5py.File(file_path, "r") as f:
            metadata = {
                "file": file_path,
                "n_samples": f.attrs["n_samples"],
                "n_params": f.attrs["n_params"],
                "n_wells": f.attrs.get("n_wells", 5),
                "n_timesteps": f.attrs.get("n_timesteps", 365),
                "param_names": [
                    n.decode("utf-8") if isinstance(n, bytes) else n
                    for n in f["param_names"][:]
                ],
                "scenario": self._extract_scenario(file_path.stem),
            }
        return metadata

    def _extract_scenario(self, file_stem: str) -> str:
        """从文件名提取场景描述。"""
        scenario = file_stem.replace("_groundwater_timeseries", "")
        scenario = scenario.replace("_", " ").title()
        return scenario

    def load_file_data(self, file_path: Path) -> tuple:
        """
        加载文件的参数数据。

        Args:
            file_path: HDF5 文件路径

        Returns:
            (params_array, param_names) 元组
        """
        with h5py.File(file_path, "r") as f:
            params_array = f["params"][:]
            param_names = [
                n.decode("utf-8") if isinstance(n, bytes) else n
                for n in f["param_names"][:]
            ]
        return params_array, param_names

    def discover_and_load_metadata(self) -> List[Dict[str, Any]]:
        """发现所有文件并加载元数据。"""
        files = self.discover_files()
        metadata_list = []

        for file_path in files:
            try:
                metadata = self.load_file_metadata(file_path)
                metadata_list.append(metadata)
                logger.info(
                    f"加载元数据: {file_path.name} - "
                    f"{metadata['n_samples']} 样本, "
                    f"场景: {metadata['scenario']}"
                )
            except Exception as e:
                logger.error(f"加载文件 {file_path} 失败: {e}")
                continue

        return metadata_list


def run_llm_pipeline(config_path: str):
    """
    运行完全 LLM 驱动的 Stage 2 管线。

    Args:
        config_path: 配置文件路径
    """
    # 加载配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger.info(f"加载配置: {config_path}")
    logger.info(f"配置内容: {json.dumps(config, indent=2, ensure_ascii=False)}")

    # 初始化 Stage 1 数据加载器
    loader = AdaptiveStage1Loader(config["stage1_data_dir"])
    metadata_list = loader.discover_and_load_metadata()

    if not metadata_list:
        raise RuntimeError("未找到任何有效的 Stage 1 数据文件")

    # 初始化 LLM 客户端
    llm_config = config.get("llm", {})
    logger.info(f"初始化 LLM 客户端: {llm_config}")

    llm_client = LLMClient(
        provider=llm_config.get("provider", "openai"),
        model=llm_config.get("model", "gpt-3.5-turbo"),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
        max_retries=llm_config.get("max_retries", 3),
        timeout=llm_config.get("timeout", 30),
    )

    # 初始化文本生成器
    text_generator = LLMTextGenerator(
        llm_client=llm_client,
        temperature=llm_config.get("temperature", 0.8),
        max_tokens=llm_config.get("max_tokens", 200),
        style_diversity=llm_config.get("style_diversity", True),
    )

    # 准备输出目录
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / config["output_file"]

    # 生成参数
    n_variants_per_sample = config.get("n_variants_per_sample", 5)
    validate_output = config.get("validate_output", True)

    # 统计信息
    total_pairs = 0
    failed_validations = 0

    # 逐文件处理
    logger.info("开始生成 Text-to-Computation 训练数据...")

    with open(output_file, "w", encoding="utf-8") as f:
        for metadata in tqdm(metadata_list, desc="处理文件"):
            file_path = metadata["file"]
            scenario = metadata["scenario"]
            n_samples = metadata["n_samples"]

            logger.info(
                f"\n处理文件: {file_path.name} "
                f"(场景: {scenario}, 样本数: {n_samples})"
            )

            # 加载参数数据
            params_array, param_names = loader.load_file_data(file_path)

            # 验证参数完整性
            required_params = {"hk", "sy", "pumping", "strt", "rch"}
            available_params = set(param_names)

            if not required_params.issubset(available_params):
                missing = required_params - available_params
                logger.warning(f"文件 {file_path.name} 缺少参数 {missing}，跳过")
                continue

            # 为每个样本生成多个文本变体
            for i in tqdm(
                range(n_samples),
                desc=f"生成样本 ({scenario})",
                leave=False,
            ):
                # 构建参数字典
                sample_params = {
                    name: float(params_array[i, j])
                    for j, name in enumerate(param_names)
                }

                # 生成多个变体
                for variant_idx in range(n_variants_per_sample):
                    try:
                        # 使用 LLM 生成文本
                        text = text_generator.generate_text(
                            sample_params,
                            scenario=scenario,
                        )

                        # 验证生成的文本（可选）
                        if validate_output:
                            is_valid = text_generator.validate_generated_text(
                                text, sample_params
                            )
                            if not is_valid:
                                logger.warning(
                                    f"验证失败，使用后备文本 "
                                    f"(样本 {i}, 变体 {variant_idx})"
                                )
                                text = text_generator._generate_fallback_text(
                                    sample_params
                                )
                                failed_validations += 1

                        # 构建输出记录
                        record = {
                            "text": text,
                            "params": sample_params,
                            "source_file": file_path.name,
                            "scenario": scenario,
                            "sample_index": i,
                            "variant_index": variant_idx,
                        }

                        # 写入 JSONL
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        total_pairs += 1

                    except Exception as e:
                        logger.error(
                            f"生成失败 (样本 {i}, 变体 {variant_idx}): {e}"
                        )
                        # 使用后备方案
                        text = text_generator._generate_fallback_text(sample_params)
                        record = {
                            "text": text,
                            "params": sample_params,
                            "source_file": file_path.name,
                            "scenario": scenario,
                            "sample_index": i,
                            "variant_index": variant_idx,
                            "fallback": True,
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        total_pairs += 1

    # 生成统计报告
    summary = {
        "output_file": str(output_file),
        "total_pairs": total_pairs,
        "n_source_files": len(metadata_list),
        "failed_validations": failed_validations,
        "validation_rate": 1.0 - (failed_validations / total_pairs if total_pairs > 0 else 0),
        "llm_config": {
            "provider": llm_config.get("provider", "openai"),
            "model": llm_config.get("model", "gpt-3.5-turbo"),
            "temperature": llm_config.get("temperature", 0.8),
        },
        "source_files": [
            {
                "file": m["file"].name,
                "scenario": m["scenario"],
                "n_samples": m["n_samples"],
                "n_params": m["n_params"],
                "n_timesteps": m["n_timesteps"],
                "n_wells": m["n_wells"],
                "param_names": m["param_names"],
            }
            for m in metadata_list
        ],
    }

    summary_file = output_dir / "data_summary_llm.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info("Stage 2 LLM 管线完成！")
    logger.info(f"{'='*60}")
    logger.info(f"输出文件: {output_file}")
    logger.info(f"统计报告: {summary_file}")
    logger.info(f"总样本对数: {total_pairs:,}")
    logger.info(f"源文件数: {len(metadata_list)}")
    logger.info(f"验证失败数: {failed_validations}")
    logger.info(f"验证通过率: {summary['validation_rate']:.2%}")


def main():
    parser = argparse.ArgumentParser(
        description="Stage 2 Text-to-Computation 训练数据生成（完全 LLM 版本）"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/data_synthesis/text2comp_llm.yaml",
        help="配置文件路径",
    )
    args = parser.parse_args()

    run_llm_pipeline(args.config)


if __name__ == "__main__":
    main()
