"""
三种扰动增强策略：Identity / Scaling / Offset。

对已生成的时序数据施加扰动，扩充数据集规模。
每种策略对时序值进行变换，同时更新对应的参数标签。
"""

import numpy as np
from typing import Dict, Any
from enum import Enum


class PerturbationType(str, Enum):
    IDENTITY = "identity"
    SCALING = "scaling"
    OFFSET = "offset"


def apply_identity(
    timeseries: np.ndarray,
    params: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Identity 扰动：不改变数据，原样返回。
    用于保持原始样本在增强后数据集中的比例。
    """
    return timeseries.copy(), params.copy()


def apply_scaling(
    timeseries: np.ndarray,
    params: np.ndarray,
    k_min: float = 0.8,
    k_max: float = 1.2,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Scaling 扰动：x' = x · k，k ∈ [k_min, k_max]。

    物理含义：模拟含水层整体水头偏移（如区域水位抬升/下降）。
    每个样本独立采样一个 k 值。

    Args:
        timeseries: [N, n_wells, n_timesteps]
        params: [N, n_params]
        k_min/k_max: 缩放系数范围
        rng: 随机数生成器

    Returns:
        扰动后的 timeseries 和 params（params 不变，扰动仅作用于输出时序）
    """
    if rng is None:
        rng = np.random.default_rng()

    N = timeseries.shape[0]
    k = rng.uniform(k_min, k_max, size=(N, 1, 1)).astype(np.float32)
    return (timeseries * k).astype(np.float32), params.copy()


def apply_offset(
    timeseries: np.ndarray,
    params: np.ndarray,
    b_std_ratio: float = 0.1,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Offset 扰动：x' = x + b，b ~ N(0, b_std_ratio · std(x))。

    物理含义：模拟观测井传感器零漂、测量误差等系统偏差。
    每个样本独立采样一个偏移量 b。

    Args:
        timeseries: [N, n_wells, n_timesteps]
        params: [N, n_params]
        b_std_ratio: 偏移量标准差 = b_std_ratio × 该样本时序的全局标准差
        rng: 随机数生成器

    Returns:
        扰动后的 timeseries 和 params（params 不变）
    """
    if rng is None:
        rng = np.random.default_rng()

    N = timeseries.shape[0]
    # 计算每个样本的全局标准差
    per_sample_std = timeseries.reshape(N, -1).std(axis=1)  # [N]
    b_std = per_sample_std * b_std_ratio                     # [N]
    b = rng.normal(0, b_std, size=N).astype(np.float32)     # [N]
    b = b[:, np.newaxis, np.newaxis]                         # [N, 1, 1]

    return (timeseries + b).astype(np.float32), params.copy()


def augment_dataset(
    timeseries: np.ndarray,
    params: np.ndarray,
    aug_cfg: Dict[str, Any],
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    对整个数据集应用三种扰动策略，返回增强后的合并数据集。

    Args:
        timeseries: 原始时序，[N, n_wells, n_timesteps]
        params: 原始参数，[N, n_params]
        aug_cfg: 增强配置（来自 modflow.yaml 的 augmentation 节）
        seed: 随机种子

    Returns:
        aug_timeseries: [N_aug, n_wells, n_timesteps]
        aug_params: [N_aug, n_params]
        aug_types: 每个样本的扰动类型标签列表，长度 N_aug
    """
    rng = np.random.default_rng(seed)
    N = timeseries.shape[0]

    # 按比例分配各扰动类型的样本数
    id_ratio = aug_cfg["identity_ratio"]
    sc_ratio = aug_cfg["scaling_ratio"]
    # offset_ratio 由剩余部分填充

    n_id = int(N * id_ratio)
    n_sc = int(N * sc_ratio)
    n_of = N - n_id - n_sc

    # 随机选取各组样本的索引（有放回采样，允许重复增强）
    idx_id = rng.choice(N, size=n_id, replace=True)
    idx_sc = rng.choice(N, size=n_sc, replace=True)
    idx_of = rng.choice(N, size=n_of, replace=True)

    ts_id, p_id = apply_identity(timeseries[idx_id], params[idx_id])
    ts_sc, p_sc = apply_scaling(
        timeseries[idx_sc],
        params[idx_sc],
        k_min=aug_cfg["scaling_k_min"],
        k_max=aug_cfg["scaling_k_max"],
        rng=rng,
    )
    ts_of, p_of = apply_offset(
        timeseries[idx_of],
        params[idx_of],
        b_std_ratio=aug_cfg["offset_b_std"],
        rng=rng,
    )

    aug_timeseries = np.concatenate([ts_id, ts_sc, ts_of], axis=0)
    aug_params = np.concatenate([p_id, p_sc, p_of], axis=0)
    aug_types = (
        [PerturbationType.IDENTITY] * n_id
        + [PerturbationType.SCALING] * n_sc
        + [PerturbationType.OFFSET] * n_of
    )

    # 打乱顺序
    shuffle_idx = rng.permutation(len(aug_types))
    aug_timeseries = aug_timeseries[shuffle_idx]
    aug_params = aug_params[shuffle_idx]
    aug_types = [aug_types[i] for i in shuffle_idx]

    return aug_timeseries, aug_params, aug_types
