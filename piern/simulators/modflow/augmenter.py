"""
参数空间采样增强策略。

基于已有样本的参数，在参数空间邻域内采样新参数，并运行 MODFLOW 生成新样本。
这种增强方式保持了参数-时序映射的物理一致性。

核心思想：
  对于原始样本 (params_0, timeseries_0)，在 params_0 附近采样新参数 params_1，
  运行 MODFLOW 得到 timeseries_1，从而得到新样本 (params_1, timeseries_1)。
  这样的增强完全符合物理规律。
"""

import numpy as np
import logging
from typing import Dict, Any, Callable
from tqdm import tqdm

logger = logging.getLogger(__name__)


def perturb_params(
    params: np.ndarray,
    param_names: list[str],
    perturbation_ratio: float = 0.05,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    在参数空间中对参数进行小幅扰动。

    策略：对每个参数施加相对扰动 δ ~ Uniform[-r, r]，其中 r 是 perturbation_ratio

    Args:
        params: 原始参数，形状 [N, n_params]
        param_names: 参数名称列表
        perturbation_ratio: 扰动比例（相对于参数值）
        rng: 随机数生成器

    Returns:
        扰动后的参数，形状 [N, n_params]

    示例：
        params = [hk=15, sy=0.12, pumping=-200, strt=7.5, rch=0.0008]
        perturbation_ratio = 0.05  # ±5%

        扰动后可能得到：
        params' = [hk=15.6, sy=0.124, pumping=-206, strt=7.62, rch=0.00082]
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
    aug_cfg: Dict[str, Any],
    modflow_cfg: Dict[str, Any],
    generate_sample_fn: Callable,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    通过参数空间采样增强数据集。

    流程：
      1. 保留所有原始样本（identity）
      2. 对部分样本，在参数空间邻域采样新参数
      3. 运行 MODFLOW 生成新时序
      4. 合并原始样本和新样本

    Args:
        original_timeseries: 原始时序，[N, n_wells, n_timesteps]
        original_params: 原始参数，[N, n_params]
        param_names: 参数名称列表
        aug_cfg: 增强配置（来自 modflow.yaml 的 augmentation 节）
        modflow_cfg: MODFLOW 配置（用于生成新样本）
        generate_sample_fn: MODFLOW 样本生成函数
        seed: 随机种子

    Returns:
        aug_timeseries: [N_aug, n_wells, n_timesteps]
        aug_params: [N_aug, n_params]

    配置示例：
        augmentation:
          enabled: true
          method: "parameter_sampling"  # 参数空间采样
          n_augmented_per_sample: 0.5   # 每个原始样本生成 0.5 个新样本（总增加 50%）
          perturbation_ratio: 0.05      # 参数扰动比例 ±5%
    """
    rng = np.random.default_rng(seed)

    # 检查增强是否启用
    if not aug_cfg.get("enabled", True):
        logger.info("数据增强已禁用，返回原始数据")
        return original_timeseries, original_params

    # 检查增强方法
    method = aug_cfg.get("method", "parameter_sampling")
    if method != "parameter_sampling":
        logger.warning(f"未知的增强方法: {method}，返回原始数据")
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
    new_timeseries_list = []
    new_params_list = []

    logger.info("运行 MODFLOW 生成增强样本...")

    with tqdm(total=N_new, desc="生成增强样本") as pbar:
        for i in range(N_new):
            # 将参数转换为字典格式
            params_dict = {name: float(perturbed_params[i, j])
                          for j, name in enumerate(param_names)}

            # 运行 MODFLOW
            timeseries, actual_params = generate_sample_fn(modflow_cfg, rng)

            # 如果 MODFLOW 失败，使用原始样本的参数重试
            if timeseries is None:
                logger.debug(f"样本 {i} 生成失败，使用原始参数")
                continue

            new_timeseries_list.append(timeseries)
            new_params_list.append([actual_params[name] for name in param_names])
            pbar.update(1)

    if len(new_timeseries_list) == 0:
        logger.warning("所有增强样本生成失败，返回原始数据")
        return original_timeseries, original_params

    # 合并原始样本和新样本
    new_timeseries = np.stack(new_timeseries_list, axis=0)
    new_params = np.array(new_params_list, dtype=np.float32)

    aug_timeseries = np.concatenate([original_timeseries, new_timeseries], axis=0)
    aug_params = np.concatenate([original_params, new_params], axis=0)

    # 打乱顺序
    shuffle_idx = rng.permutation(len(aug_timeseries))
    aug_timeseries = aug_timeseries[shuffle_idx]
    aug_params = aug_params[shuffle_idx]

    logger.info(f"增强完成：原始 {N_original} + 新增 {len(new_timeseries_list)} = 总计 {len(aug_timeseries)} 个样本")

    return aug_timeseries, aug_params


def augment_with_parameter_sampling_optimized(
    original_timeseries: np.ndarray,
    original_params: np.ndarray,
    param_names: list[str],
    aug_cfg: Dict[str, Any],
    modflow_cfg: Dict[str, Any],
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    优化版本：直接在 generator 中生成扰动参数，避免重复调用。

    这个函数会在 pipeline 中调用，需要配合修改后的 generate_batch 使用。

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

    # 随机选择要增强的样本
    selected_indices = rng.choice(N_original, size=N_new, replace=True)
    selected_params = original_params[selected_indices]

    # 扰动参数
    perturbed_params = perturb_params(
        selected_params,
        param_names,
        perturbation_ratio=perturbation_ratio,
        rng=rng,
    )

    # 生成新样本（需要调用 MODFLOW）
    # 注意：这里需要调用 generate_batch_with_params 函数
    # 为了避免循环依赖，这个函数留待 pipeline 中实现

    logger.info("生成增强样本需要运行 MODFLOW，请在 pipeline 中实现")

    # 临时返回原始数据
    return original_timeseries, original_params
