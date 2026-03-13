"""
自动生成多样化的 MODFLOW 配置文件。

多样化策略：
1. 参数范围变化：不同地质条件（高渗透/低渗透、强抽水/弱抽水等）
2. 网格分辨率：粗网格/细网格
3. 时间尺度：短期/中期/长期模拟
4. 观测井配置：数量、位置分布
5. 水文地质场景：不同的边界条件、补给模式
"""

import yaml
import numpy as np
from pathlib import Path
from typing import Dict, Any, List


class MODFLOWConfigGenerator:
    """MODFLOW 配置生成器。"""

    def __init__(self, output_dir: str = "configs/data_synthesis/modflow_variants"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_configs(self) -> List[str]:
        """生成所有配置变体。"""
        config_files = []

        # 1. 基准配置（已有）
        config_files.append(self._generate_baseline_config())

        # 2. 地质条件变体
        config_files.extend(self._generate_geological_variants())

        # 3. 时空尺度变体
        config_files.extend(self._generate_spatiotemporal_variants())

        # 4. 抽水强度变体
        config_files.extend(self._generate_pumping_variants())

        # 5. 混合场景
        config_files.extend(self._generate_mixed_scenarios())

        return config_files

    def _generate_baseline_config(self) -> str:
        """生成基准配置（与现有配置一致）。"""
        config = {
            "output_dir": "data/modflow",
            "output_file": "baseline_groundwater_timeseries.h5",
            "n_samples": 1000,
            "n_timesteps": 365,
            "n_wells": 5,
            "grid": {
                "nrow": 20,
                "ncol": 20,
                "nlay": 1,
                "delr": 100.0,
                "delc": 100.0,
                "top": 10.0,
                "botm": 0.0,
            },
            "params": {
                "hk_min": 1.0,
                "hk_max": 50.0,
                "sy_min": 0.05,
                "sy_max": 0.30,
                "pumping_min": -500.0,
                "pumping_max": -50.0,
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.0001,
                "rch_max": 0.002,
            },
            "augmentation": {
                "identity_ratio": 0.4,
                "scaling_ratio": 0.3,
                "offset_ratio": 0.3,
                "scaling_k_min": 0.8,
                "scaling_k_max": 1.2,
                "offset_b_std": 0.1,
            },
            "validation": {
                "max_nan_ratio": 0.05,
                "min_variance": 0.000001,
                "max_head_value": 15.0,
                "min_head_value": -5.0,
            },
            "seed": 42,
        }

        return self._save_config(config, "baseline.yaml")

    def _generate_geological_variants(self) -> List[str]:
        """生成不同地质条件的配置。"""
        configs = []

        # 高渗透含水层（砾石、粗砂）
        high_perm = self._create_variant(
            name="high_permeability",
            description="高渗透含水层（砾石、粗砂）",
            n_samples=500,
            params={
                "hk_min": 20.0,
                "hk_max": 100.0,  # 更高的渗透系数
                "sy_min": 0.20,
                "sy_max": 0.35,   # 更高的给水度
                "pumping_min": -800.0,
                "pumping_max": -200.0,
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.001,
                "rch_max": 0.005,  # 更强的补给
            },
        )
        configs.append(high_perm)

        # 低渗透含水层（粉砂、粘土）
        low_perm = self._create_variant(
            name="low_permeability",
            description="低渗透含水层（粉砂、粘土）",
            n_samples=500,
            params={
                "hk_min": 0.1,
                "hk_max": 5.0,    # 更低的渗透系数
                "sy_min": 0.01,
                "sy_max": 0.10,   # 更低的给水度
                "pumping_min": -100.0,
                "pumping_max": -10.0,  # 较弱的抽水
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.00001,
                "rch_max": 0.0005,  # 较弱的补给
            },
        )
        configs.append(low_perm)

        # 中等渗透含水层（细砂、中砂）
        medium_perm = self._create_variant(
            name="medium_permeability",
            description="中等渗透含水层（细砂、中砂）",
            n_samples=500,
            params={
                "hk_min": 5.0,
                "hk_max": 25.0,
                "sy_min": 0.10,
                "sy_max": 0.25,
                "pumping_min": -300.0,
                "pumping_max": -50.0,
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.0002,
                "rch_max": 0.002,
            },
        )
        configs.append(medium_perm)

        return configs

    def _generate_spatiotemporal_variants(self) -> List[str]:
        """生成不同时空尺度的配置。"""
        configs = []

        # 短期模拟（30 天，日尺度）
        short_term = self._create_variant(
            name="short_term_daily",
            description="短期模拟（30 天，日尺度）",
            n_samples=500,
            n_timesteps=30,
            n_wells=3,  # 较少观测井
        )
        configs.append(short_term)

        # 中期模拟（180 天，半年）
        medium_term = self._create_variant(
            name="medium_term_halfyear",
            description="中期模拟（180 天，半年）",
            n_samples=500,
            n_timesteps=180,
            n_wells=5,
        )
        configs.append(medium_term)

        # 长期模拟（730 天，2 年）
        long_term = self._create_variant(
            name="long_term_twoyears",
            description="长期模拟（730 天，2 年）",
            n_samples=300,
            n_timesteps=730,
            n_wells=7,  # 更多观测井
        )
        configs.append(long_term)

        # 细网格（40×40）
        fine_grid = self._create_variant(
            name="fine_grid_40x40",
            description="细网格（40×40，空间分辨率更高）",
            n_samples=300,
            grid={
                "nrow": 40,
                "ncol": 40,
                "nlay": 1,
                "delr": 50.0,  # 更小的网格间距
                "delc": 50.0,
                "top": 10.0,
                "botm": 0.0,
            },
            n_wells=9,  # 更多观测井
        )
        configs.append(fine_grid)

        # 粗网格（10×10）
        coarse_grid = self._create_variant(
            name="coarse_grid_10x10",
            description="粗网格（10×10，区域尺度）",
            n_samples=500,
            grid={
                "nrow": 10,
                "ncol": 10,
                "nlay": 1,
                "delr": 200.0,  # 更大的网格间距
                "delc": 200.0,
                "top": 10.0,
                "botm": 0.0,
            },
            n_wells=3,
        )
        configs.append(coarse_grid)

        return configs

    def _generate_pumping_variants(self) -> List[str]:
        """生成不同抽水强度的配置。"""
        configs = []

        # 强抽水场景
        heavy_pumping = self._create_variant(
            name="heavy_pumping",
            description="强抽水场景（过度开采）",
            n_samples=500,
            params={
                "hk_min": 5.0,
                "hk_max": 30.0,
                "sy_min": 0.10,
                "sy_max": 0.25,
                "pumping_min": -1000.0,  # 强抽水
                "pumping_max": -500.0,
                "strt_min": 7.0,
                "strt_max": 9.0,
                "rch_min": 0.0001,
                "rch_max": 0.001,   # 补给不足
            },
        )
        configs.append(heavy_pumping)

        # 弱抽水场景
        light_pumping = self._create_variant(
            name="light_pumping",
            description="弱抽水场景（合理开采）",
            n_samples=500,
            params={
                "hk_min": 5.0,
                "hk_max": 30.0,
                "sy_min": 0.10,
                "sy_max": 0.25,
                "pumping_min": -100.0,  # 弱抽水
                "pumping_max": -20.0,
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.0005,
                "rch_max": 0.003,   # 充足补给
            },
        )
        configs.append(light_pumping)

        # 注水场景（人工补给）
        injection = self._create_variant(
            name="artificial_recharge",
            description="人工补给场景（注水）",
            n_samples=300,
            params={
                "hk_min": 5.0,
                "hk_max": 30.0,
                "sy_min": 0.10,
                "sy_max": 0.25,
                "pumping_min": 50.0,   # 正值表示注水
                "pumping_max": 500.0,
                "strt_min": 5.0,
                "strt_max": 7.0,
                "rch_min": 0.0001,
                "rch_max": 0.001,
            },
        )
        configs.append(injection)

        return configs

    def _generate_mixed_scenarios(self) -> List[str]:
        """生成混合场景（组合不同条件）。"""
        configs = []

        # 干旱区场景（低补给 + 中等抽水）
        arid = self._create_variant(
            name="arid_region",
            description="干旱区场景（低补给、中等抽水）",
            n_samples=400,
            params={
                "hk_min": 3.0,
                "hk_max": 20.0,
                "sy_min": 0.05,
                "sy_max": 0.15,
                "pumping_min": -300.0,
                "pumping_max": -100.0,
                "strt_min": 5.0,
                "strt_max": 7.0,
                "rch_min": 0.00001,  # 极低补给
                "rch_max": 0.0003,
            },
        )
        configs.append(arid)

        # 湿润区场景（高补给 + 弱抽水）
        humid = self._create_variant(
            name="humid_region",
            description="湿润区场景（高补给、弱抽水）",
            n_samples=400,
            params={
                "hk_min": 10.0,
                "hk_max": 50.0,
                "sy_min": 0.15,
                "sy_max": 0.30,
                "pumping_min": -200.0,
                "pumping_max": -50.0,
                "strt_min": 6.0,
                "strt_max": 9.0,
                "rch_min": 0.002,   # 高补给
                "rch_max": 0.008,
            },
        )
        configs.append(humid)

        # 城市供水场景（中高渗透 + 强抽水 + 短期）
        urban = self._create_variant(
            name="urban_water_supply",
            description="城市供水场景（强抽水、短期）",
            n_samples=400,
            n_timesteps=90,
            params={
                "hk_min": 15.0,
                "hk_max": 40.0,
                "sy_min": 0.15,
                "sy_max": 0.25,
                "pumping_min": -800.0,
                "pumping_max": -300.0,
                "strt_min": 6.0,
                "strt_max": 8.0,
                "rch_min": 0.0003,
                "rch_max": 0.002,
            },
        )
        configs.append(urban)

        return configs

    def _create_variant(
        self,
        name: str,
        description: str,
        n_samples: int = 1000,
        n_timesteps: int = 365,
        n_wells: int = 5,
        grid: Dict[str, Any] = None,
        params: Dict[str, float] = None,
    ) -> str:
        """创建配置变体。"""

        # 基础配置
        config = {
            "description": description,
            "output_dir": "data/modflow",
            "output_file": f"{name}_groundwater_timeseries.h5",
            "n_samples": n_samples,
            "n_timesteps": n_timesteps,
            "n_wells": n_wells,
            "grid": grid or {
                "nrow": 20,
                "ncol": 20,
                "nlay": 1,
                "delr": 100.0,
                "delc": 100.0,
                "top": 10.0,
                "botm": 0.0,
            },
            "params": params or {
                "hk_min": 1.0,
                "hk_max": 50.0,
                "sy_min": 0.05,
                "sy_max": 0.30,
                "pumping_min": -500.0,
                "pumping_max": -50.0,
                "strt_min": 5.0,
                "strt_max": 9.0,
                "rch_min": 0.0001,
                "rch_max": 0.002,
            },
            "augmentation": {
                "identity_ratio": 0.4,
                "scaling_ratio": 0.3,
                "offset_ratio": 0.3,
                "scaling_k_min": 0.8,
                "scaling_k_max": 1.2,
                "offset_b_std": 0.1,
            },
            "validation": {
                "max_nan_ratio": 0.05,
                "min_variance": 0.000001,
                "max_head_value": 20.0,  # 放宽范围
                "min_head_value": -10.0,
            },
            "seed": hash(name) % 10000,  # 基于名称生成不同种子
        }

        return self._save_config(config, f"{name}.yaml")

    def _save_config(self, config: Dict[str, Any], filename: str) -> str:
        """保存配置文件。"""
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            # 添加注释头
            f.write(f"# {config.get('description', 'MODFLOW 数据生成配置')}\n")
            f.write(f"# 自动生成，请勿手动编辑\n\n")
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)

        print(f"✓ 生成配置: {filepath}")
        return str(filepath)

    def generate_summary(self, config_files: List[str]) -> str:
        """生成配置摘要文档。"""
        summary_path = self.output_dir / "README.md"

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("# MODFLOW 配置变体库\n\n")
            f.write("自动生成的多样化 MODFLOW 数据生成配置。\n\n")
            f.write(f"**总配置数**: {len(config_files)}\n\n")

            # 统计信息
            total_samples = 0
            configs_by_category = {
                "基准配置": [],
                "地质条件变体": [],
                "时空尺度变体": [],
                "抽水强度变体": [],
                "混合场景": [],
            }

            for config_file in config_files:
                with open(config_file, "r", encoding="utf-8") as cf:
                    config = yaml.safe_load(cf)
                    total_samples += config["n_samples"]

                    # 分类
                    name = Path(config_file).stem
                    if "baseline" in name:
                        configs_by_category["基准配置"].append((name, config))
                    elif any(x in name for x in ["permeability"]):
                        configs_by_category["地质条件变体"].append((name, config))
                    elif any(x in name for x in ["term", "grid"]):
                        configs_by_category["时空尺度变体"].append((name, config))
                    elif any(x in name for x in ["pumping", "recharge"]):
                        configs_by_category["抽水强度变体"].append((name, config))
                    else:
                        configs_by_category["混合场景"].append((name, config))

            f.write(f"**预计总样本数**: {total_samples}\n\n")
            f.write("---\n\n")

            # 详细列表
            for category, configs in configs_by_category.items():
                if not configs:
                    continue

                f.write(f"## {category}\n\n")
                for name, config in configs:
                    f.write(f"### {name}\n\n")
                    f.write(f"**描述**: {config.get('description', 'N/A')}\n\n")
                    f.write(f"- 样本数: {config['n_samples']}\n")
                    f.write(f"- 时间步: {config['n_timesteps']} 天\n")
                    f.write(f"- 观测井: {config['n_wells']} 个\n")
                    f.write(f"- 网格: {config['grid']['nrow']}×{config['grid']['ncol']}\n")

                    # 参数范围
                    params = config["params"]
                    f.write(f"- 参数范围:\n")
                    f.write(f"  - hk: [{params['hk_min']}, {params['hk_max']}] m/day\n")
                    f.write(f"  - sy: [{params['sy_min']}, {params['sy_max']}]\n")
                    f.write(f"  - pumping: [{params['pumping_min']}, {params['pumping_max']}] m³/day\n")
                    f.write(f"  - rch: [{params['rch_min']}, {params['rch_max']}] m/day\n")

                    f.write(f"\n**配置文件**: `{name}.yaml`\n\n")
                    f.write("---\n\n")

        print(f"✓ 生成摘要: {summary_path}")
        return str(summary_path)


def main():
    print("=" * 70)
    print("MODFLOW 配置生成器")
    print("=" * 70)
    print()

    generator = MODFLOWConfigGenerator()

    print("正在生成配置文件...")
    print()
    config_files = generator.generate_all_configs()

    print()
    print(f"✓ 共生成 {len(config_files)} 个配置文件")
    print()

    print("正在生成摘要文档...")
    summary_file = generator.generate_summary(config_files)

    print()
    print("=" * 70)
    print("完成！")
    print("=" * 70)
    print()
    print(f"配置目录: {generator.output_dir}")
    print(f"摘要文档: {summary_file}")
    print()
    print("下一步：运行批量生成脚本")
    print("  python scripts/data_synthesis/batch_generate_modflow.py")


if __name__ == "__main__":
    main()
