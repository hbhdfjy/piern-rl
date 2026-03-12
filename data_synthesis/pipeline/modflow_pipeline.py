"""
MODFLOW 数据合成完整管线。

流程：
  参数采样
    ↓
  flopy/MODFLOW 正演（generate_batch）
    ↓
  质量过滤（filter_dataset）
    ↓
  扰动增强（augment_dataset）
    ↓
  HDF5 存储（save_dataset）

用法：
  python -m data_synthesis.pipeline.modflow_pipeline \
      --config configs/data_synthesis/modflow.yaml
"""

import argparse
import logging
import os
import time

import numpy as np
import yaml

from data_synthesis.generators.modflow_generator import generate_batch
from data_synthesis.augmenters.perturbation import augment_dataset
from data_synthesis.validators.quality_filter import filter_dataset
from data_synthesis.utils.hdf5_writer import save_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_pipeline(cfg_path: str) -> str:
    """
    执行完整合成管线。

    Args:
        cfg_path: YAML 配置文件路径

    Returns:
        输出 HDF5 文件路径
    """
    # 加载配置
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    n_samples = cfg["n_samples"]
    seed = cfg.get("seed", 42)
    output_path = os.path.join(cfg["output_dir"], cfg["output_file"])

    logger.info(f"===== MODFLOW 数据合成管线启动 =====")
    logger.info(f"目标样本数: {n_samples}")
    logger.info(f"输出路径: {output_path}")

    t0 = time.time()

    # Step 1: 生成原始数据
    logger.info("Step 1/4: 运行 MODFLOW 正演...")
    timeseries, params, param_names = generate_batch(cfg, n_samples, seed=seed)
    logger.info(f"  → 生成 {timeseries.shape[0]} 个样本，形状 {timeseries.shape}")

    # Step 2: 质量过滤
    logger.info("Step 2/4: 质量过滤...")
    timeseries, params, _ = filter_dataset(timeseries, params, cfg["validation"])
    logger.info(f"  → 过滤后保留 {timeseries.shape[0]} 个样本")

    if timeseries.shape[0] == 0:
        raise RuntimeError("质量过滤后无有效样本，请检查 MODFLOW 配置或验证阈值")

    # Step 3: 扰动增强
    logger.info("Step 3/4: 扰动增强...")
    aug_ts, aug_params, aug_types = augment_dataset(
        timeseries, params, cfg["augmentation"], seed=seed + 1
    )
    logger.info(f"  → 增强后共 {aug_ts.shape[0]} 个样本")

    # Step 4: 存储
    logger.info("Step 4/4: 写入 HDF5...")
    type_counts = {
        "identity": aug_types.count("identity"),
        "scaling": aug_types.count("scaling"),
        "offset": aug_types.count("offset"),
    }
    metadata = {
        "config_path": cfg_path,
        "n_original": timeseries.shape[0],
        "n_augmented": aug_ts.shape[0],
        "augmentation_counts": list(type_counts.values()),
        "augmentation_types": ["identity", "scaling", "offset"],
        "param_names": param_names,
    }
    save_dataset(output_path, aug_ts, aug_params, param_names, metadata)

    elapsed = time.time() - t0
    logger.info(f"===== 完成！耗时 {elapsed:.1f}s =====")
    logger.info(f"数据集形状: timeseries={aug_ts.shape}, params={aug_params.shape}")
    logger.info(f"增强分布: identity={type_counts['identity']}, "
                f"scaling={type_counts['scaling']}, offset={type_counts['offset']}")
    logger.info(f"输出文件: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="MODFLOW 地下水位时序数据合成管线")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/data_synthesis/modflow.yaml",
        help="配置文件路径",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        raise FileNotFoundError(f"配置文件不存在: {args.config}")

    run_pipeline(args.config)


if __name__ == "__main__":
    main()
