"""
MODFLOW 数据合成管线 V2 - 支持参数空间采样增强。

改进点：
  1. 删除无物理意义的 Scaling/Offset 扰动
  2. 使用参数空间采样增强（在参数邻域采样 → 运行 MODFLOW）
  3. 保持参数-时序映射的物理一致性

流程：
  参数采样
    ↓
  MODFLOW 正演（generate_batch）
    ↓
  质量过滤（filter_dataset）
    ↓
  参数空间采样增强（augment_with_parameter_sampling）
    ├─ 在原始参数邻域采样新参数
    ├─ 运行 MODFLOW 生成新时序
    └─ 合并原始样本和新样本
    ↓
  HDF5 存储（save_dataset）

用法：
  python -m data_synthesis.pipeline.modflow_pipeline_v2 \
      --config configs/data_synthesis/modflow.yaml
"""

import argparse
import logging
import os
import time

import numpy as np
import yaml

from data_synthesis.generators.modflow_generator import generate_batch
from data_synthesis.generators.modflow_generator_with_params import generate_batch_from_params
from data_synthesis.validators.quality_filter import filter_dataset
from data_synthesis.utils.hdf5_writer import save_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def perturb_params(
    params: np.ndarray,
    param_names: list[str],
    perturbation_ratio: float = 0.05,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    在参数空间中对参数进行小幅扰动。

    Args:
        params: 原始参数，形状 [N, n_params]
        param_names: 参数名称列表
        perturbation_ratio: 扰动比例（相对于参数值）
        rng: 随机数生成器

    Returns:
        扰动后的参数，形状 [N, n_params]
    """
    if rng is None:
        rng = np.random.default_rng()

    N, n_params = params.shape

    # 为每个参数生成扰动因子：1 + δ，δ ~ Uniform[-r, r]
    delta = rng.uniform(-perturbation_ratio, perturbation_ratio, size=(N, n_params))
    perturbed_params = params * (1.0 + delta)

    return perturbed_params.astype(np.float32)


def augment_with_parameter_sampling(
    original_timeseries: np.ndarray,
    original_params: np.ndarray,
    param_names: list[str],
    aug_cfg: dict,
    modflow_cfg: dict,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    通过参数空间采样增强数据集。

    Args:
        original_timeseries: 原始时序，[N, n_wells, n_timesteps]
        original_params: 原始参数，[N, n_params]
        param_names: 参数名称列表
        aug_cfg: 增强配置
        modflow_cfg: MODFLOW 配置
        seed: 随机种子

    Returns:
        aug_timeseries: [N_aug, n_wells, n_timesteps]
        aug_params: [N_aug, n_params]
    """
    rng = np.random.default_rng(seed)

    # 检查增强是否启用
    if not aug_cfg.get("enabled", True):
        logger.info("数据增强已禁用，返回原始数据")
        return original_timeseries, original_params

    N_original = original_timeseries.shape[0]
    n_augmented_per_sample = aug_cfg.get("n_augmented_per_sample", 0.5)
    perturbation_ratio = aug_cfg.get("perturbation_ratio", 0.05)

    # 计算要生成的新样本数
    N_new = int(N_original * n_augmented_per_sample)

    if N_new == 0:
        logger.info("增强样本数为 0，返回原始数据")
        return original_timeseries, original_params

    logger.info(f"参数空间采样增强：原始 {N_original} 个样本，将生成 {N_new} 个新样本")
    logger.info(f"  - 扰动比例: ±{perturbation_ratio*100:.1f}%")

    # 随机选择要增强的样本（有放回采样）
    selected_indices = rng.choice(N_original, size=N_new, replace=True)
    selected_params = original_params[selected_indices]

    # 扰动参数
    perturbed_params = perturb_params(
        selected_params,
        param_names,
        perturbation_ratio=perturbation_ratio,
        rng=rng,
    )

    # 为扰动后的参数生成新时序
    new_timeseries, new_params = generate_batch_from_params(
        perturbed_params,
        param_names,
        modflow_cfg,
    )

    if len(new_timeseries) == 0:
        logger.warning("所有增强样本生成失败，返回原始数据")
        return original_timeseries, original_params

    # 合并原始样本和新样本
    aug_timeseries = np.concatenate([original_timeseries, new_timeseries], axis=0)
    aug_params = np.concatenate([original_params, new_params], axis=0)

    # 打乱顺序
    shuffle_idx = rng.permutation(len(aug_timeseries))
    aug_timeseries = aug_timeseries[shuffle_idx]
    aug_params = aug_params[shuffle_idx]

    logger.info(f"增强完成：原始 {N_original} + 新增 {len(new_timeseries)} = 总计 {len(aug_timeseries)} 个样本")

    return aug_timeseries, aug_params


def run_pipeline(cfg_path: str) -> str:
    """
    执行完整合成管线（V2 版本）。

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

    logger.info(f"===== MODFLOW 数据合成管线 V2 启动 =====")
    logger.info(f"目标样本数: {n_samples}")
    logger.info(f"输出路径: {output_path}")
    logger.info(f"增强方法: 参数空间采样")

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

    # Step 3: 参数空间采样增强
    logger.info("Step 3/4: 参数空间采样增强...")
    aug_ts, aug_params = augment_with_parameter_sampling(
        timeseries, params, param_names, cfg["augmentation"], cfg, seed=seed + 1
    )
    logger.info(f"  → 增强后共 {aug_ts.shape[0]} 个样本")

    # Step 4: 存储
    logger.info("Step 4/4: 写入 HDF5...")
    metadata = {
        "config_path": cfg_path,
        "n_original": timeseries.shape[0],
        "n_augmented": aug_ts.shape[0],
        "augmentation_method": "parameter_sampling",
        "augmentation_config": cfg["augmentation"],
        "param_names": param_names,
    }
    save_dataset(output_path, aug_ts, aug_params, param_names, metadata)

    elapsed = time.time() - t0
    logger.info(f"===== 完成！耗时 {elapsed:.1f}s =====")
    logger.info(f"数据集形状: timeseries={aug_ts.shape}, params={aug_params.shape}")
    logger.info(f"增强比例: {(aug_ts.shape[0] - timeseries.shape[0]) / timeseries.shape[0] * 100:.1f}%")
    logger.info(f"输出文件: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="MODFLOW 地下水位时序数据合成管线 V2")
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
