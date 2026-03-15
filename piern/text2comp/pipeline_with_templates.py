"""
Stage 2 Text-to-Computation 训练数据生成管线（基于预生成模板）。

使用预先生成的100条场景模板，填充参数值生成训练数据。
"""

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Any
import h5py
import yaml
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TemplatePipeline:
    """基于模板的 Stage 2 数据生成管线"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """加载预生成的场景模板"""
        template_path = Path(self.config.get("template_path", "data/text2comp/scenario_templates.json"))

        if not template_path.exists():
            raise FileNotFoundError(
                f"模板文件不存在: {template_path}\n"
                f"请先运行: python -m piern.text2comp.template_generator"
            )

        with open(template_path, "r", encoding="utf-8") as f:
            templates = json.load(f)

        logger.info(f"加载了 {len(templates)} 个场景的模板")
        for scenario, tmpl_list in templates.items():
            logger.info(f"  - {scenario}: {len(tmpl_list)} 条模板")

        return templates

    def _extract_scenario_key(self, file_path: Path) -> str:
        """从文件名提取场景键名"""
        # 例如: "baseline_groundwater_timeseries.h5" -> "baseline"
        stem = file_path.stem.replace("_groundwater_timeseries", "")
        return stem

    def _fill_template(self, template: str, params: Dict[str, float]) -> str:
        """填充模板中的参数占位符"""
        text = template
        for param_name, param_value in params.items():
            placeholder = f"{{{{{param_name}}}}}"
            # 格式化数值（保留合理的小数位）
            if param_name in ["hk", "pumping"]:
                formatted_value = f"{param_value:.1f}"
            elif param_name in ["sy", "rch"]:
                formatted_value = f"{param_value:.4f}"
            elif param_name in ["strt"]:
                formatted_value = f"{param_value:.2f}"
            else:
                formatted_value = f"{param_value:.3f}"

            text = text.replace(placeholder, formatted_value)

        return text

    def generate_for_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """为单个 HDF5 文件生成训练数据"""
        scenario_key = self._extract_scenario_key(file_path)

        # 检查是否有对应的模板
        if scenario_key not in self.templates:
            logger.warning(f"场景 '{scenario_key}' 没有对应的模板，跳过")
            return []

        templates = self.templates[scenario_key]
        logger.info(f"处理文件: {file_path.name} (场景: {scenario_key}, {len(templates)} 条模板)")

        # 加载参数数据
        with h5py.File(file_path, "r") as f:
            params_array = f["params"][:]
            param_names = [
                n.decode("utf-8") if isinstance(n, bytes) else n
                for n in f["param_names"][:]
            ]

        n_samples = len(params_array)
        training_pairs = []

        # 为每个样本随机选择一个模板
        for i in tqdm(range(n_samples), desc=f"  生成文本对"):
            # 随机选择一个模板
            template = random.choice(templates)

            # 构建参数字典
            params_dict = {name: float(params_array[i, j]) for j, name in enumerate(param_names)}

            # 填充模板
            text = self._fill_template(template, params_dict)

            # 构建训练对
            training_pair = {
                "text": text,
                "params": params_dict,
                "scenario": scenario_key,
                "template_id": templates.index(template),  # 记录使用的模板ID
            }

            training_pairs.append(training_pair)

        return training_pairs

    def run(self):
        """运行完整的 Stage 2 管线"""
        logger.info("=" * 60)
        logger.info("Stage 2 Text-to-Computation 数据生成（基于模板）")
        logger.info("=" * 60)

        # 发现所有 Stage 1 数据文件
        stage1_dir = Path(self.config["stage1_data_dir"])
        pattern = "*_groundwater_timeseries.h5"
        stage1_files = sorted(stage1_dir.glob(pattern))

        if not stage1_files:
            raise FileNotFoundError(f"在 {stage1_dir} 中未找到匹配 {pattern} 的文件")

        logger.info(f"发现 {len(stage1_files)} 个 Stage 1 数据文件")

        # 为每个文件生成训练数据
        all_training_pairs = []

        for file_path in stage1_files:
            pairs = self.generate_for_file(file_path)
            all_training_pairs.extend(pairs)

        # 保存到 JSONL
        output_dir = Path(self.config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.config["output_file"]

        logger.info(f"保存 {len(all_training_pairs)} 条训练数据到: {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            for pair in all_training_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        # 生成统计报告
        self._generate_summary(all_training_pairs, output_dir)

        logger.info("=" * 60)
        logger.info("Stage 2 数据生成完成！")
        logger.info(f"  - 总训练对数: {len(all_training_pairs):,}")
        logger.info(f"  - 输出文件: {output_path}")
        logger.info("=" * 60)

    def _generate_summary(self, training_pairs: List[Dict[str, Any]], output_dir: Path):
        """生成统计摘要"""
        summary = {
            "total_pairs": len(training_pairs),
            "scenarios": {},
        }

        # 按场景统计
        for pair in training_pairs:
            scenario = pair["scenario"]
            if scenario not in summary["scenarios"]:
                summary["scenarios"][scenario] = {
                    "count": 0,
                    "templates_used": set(),
                }

            summary["scenarios"][scenario]["count"] += 1
            summary["scenarios"][scenario]["templates_used"].add(pair["template_id"])

        # 转换 set 为 list（JSON 序列化）
        for scenario in summary["scenarios"]:
            summary["scenarios"][scenario]["templates_used"] = len(
                summary["scenarios"][scenario]["templates_used"]
            )

        # 保存摘要
        summary_path = output_dir / "data_summary_templates.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"统计摘要已保存: {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Stage 2 数据生成（基于模板）")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/text2comp/default.yaml",
        help="配置文件路径",
    )
    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 运行管线
    pipeline = TemplatePipeline(config)
    pipeline.run()


if __name__ == "__main__":
    main()
