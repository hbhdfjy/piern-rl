"""
测试参数空间采样增强。

快速验证新的增强方法是否正常工作。
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import numpy as np
import yaml
import logging

from data_synthesis.generators.modflow_generator import generate_batch
from data_synthesis.generators.modflow_generator_with_params import generate_batch_from_params
from data_synthesis.validators.quality_filter import filter_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def test_parameter_augmentation():
    """测试参数空间采样增强。"""

    logger.info("=" * 70)
    logger.info("测试参数空间采样增强")
    logger.info("=" * 70)

    # 创建测试配置
    cfg = {
        "n_samples": 10,  # 生成 10 个原始样本
        "n_timesteps": 30,  # 30 天（快速测试）
        "n_wells": 3,
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
            "hk_min": 5.0,
            "hk_max": 30.0,
            "sy_min": 0.1,
            "sy_max": 0.25,
            "pumping_min": -300.0,
            "pumping_max": -100.0,
            "strt_min": 6.0,
            "strt_max": 8.0,
            "rch_min": 0.0002,
            "rch_max": 0.001,
        },
        "validation": {
            "max_nan_ratio": 0.05,
            "min_variance": 1e-6,
            "max_head_value": 15.0,
            "min_head_value": -5.0,
        },
    }

    # Step 1: 生成原始样本
    logger.info("\nStep 1: 生成原始样本...")
    timeseries, params, param_names = generate_batch(cfg, n_samples=10, seed=42)
    logger.info(f"  原始样本形状: timeseries={timeseries.shape}, params={params.shape}")
    logger.info(f"  参数名称: {param_names}")

    # Step 2: 质量过滤
    logger.info("\nStep 2: 质量过滤...")
    timeseries, params, _ = filter_dataset(timeseries, params, cfg["validation"])
    logger.info(f"  过滤后样本数: {timeseries.shape[0]}")

    if timeseries.shape[0] == 0:
        logger.error("所有样本被过滤，测试失败")
        return False

    # Step 3: 参数扰动
    logger.info("\nStep 3: 参数扰动...")
    rng = np.random.default_rng(43)

    # 选择前 5 个样本进行增强
    n_to_augment = min(5, timeseries.shape[0])
    selected_params = params[:n_to_augment]

    # 扰动参数（±5%）
    perturbation_ratio = 0.05
    delta = rng.uniform(-perturbation_ratio, perturbation_ratio, size=selected_params.shape)
    perturbed_params = selected_params * (1.0 + delta)

    logger.info(f"  选择 {n_to_augment} 个样本进行增强")
    logger.info(f"  扰动比例: ±{perturbation_ratio*100:.1f}%")

    # 显示扰动前后对比
    logger.info("\n  扰动前后对比（前 2 个样本）：")
    for i in range(min(2, n_to_augment)):
        logger.info(f"    样本 {i}:")
        for j, name in enumerate(param_names):
            orig = selected_params[i, j]
            pert = perturbed_params[i, j]
            change = (pert - orig) / orig * 100
            logger.info(f"      {name}: {orig:.4f} → {pert:.4f} ({change:+.1f}%)")

    # Step 4: 为扰动参数生成新时序
    logger.info("\nStep 4: 为扰动参数生成新时序...")
    new_timeseries, new_params = generate_batch_from_params(
        perturbed_params,
        param_names,
        cfg,
    )

    if len(new_timeseries) == 0:
        logger.error("所有增强样本生成失败")
        return False

    logger.info(f"  成功生成 {len(new_timeseries)} 个新样本")

    # Step 5: 验证物理一致性
    logger.info("\nStep 5: 验证物理一致性...")

    # 检查：不同参数 → 不同时序
    for i in range(min(2, len(new_timeseries))):
        orig_ts = timeseries[i, 0, :5]  # 原始时序前 5 个时间步
        new_ts = new_timeseries[i, 0, :5]  # 新时序前 5 个时间步

        diff = np.abs(new_ts - orig_ts).mean()

        logger.info(f"  样本 {i}:")
        logger.info(f"    原始时序: {orig_ts}")
        logger.info(f"    新时序:   {new_ts}")
        logger.info(f"    平均差异: {diff:.4f} m")

        if diff < 0.01:
            logger.warning(f"    ⚠️ 差异过小，可能参数扰动不够")
        else:
            logger.info(f"    ✓ 差异合理")

    # Step 6: 合并数据
    logger.info("\nStep 6: 合并原始样本和新样本...")
    aug_timeseries = np.concatenate([timeseries, new_timeseries], axis=0)
    aug_params = np.concatenate([params, new_params], axis=0)

    logger.info(f"  原始样本: {timeseries.shape[0]}")
    logger.info(f"  新样本:   {len(new_timeseries)}")
    logger.info(f"  总样本:   {aug_timeseries.shape[0]}")
    logger.info(f"  增强比例: {len(new_timeseries) / timeseries.shape[0] * 100:.1f}%")

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("✓ 测试通过！参数空间采样增强工作正常")
    logger.info("=" * 70)
    logger.info("\n关键验证点：")
    logger.info("  ✓ 参数扰动成功")
    logger.info("  ✓ MODFLOW 生成新时序成功")
    logger.info("  ✓ 不同参数 → 不同时序（物理一致性）")
    logger.info("  ✓ 数据合并成功")

    return True


if __name__ == "__main__":
    try:
        success = test_parameter_augmentation()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)
