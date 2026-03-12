"""HDF5 存储工具：将合成的时序数据集写入 HDF5 文件。"""

import numpy as np
import h5py
import os
from typing import Dict, Any


def save_dataset(
    output_path: str,
    timeseries: np.ndarray,
    params: np.ndarray,
    param_names: list[str],
    metadata: Dict[str, Any] | None = None,
) -> None:
    """
    将合成数据集写入 HDF5 文件。

    Args:
        output_path: 输出文件路径（.h5）
        timeseries: 时序数据，形状 [N, n_wells, n_timesteps]
        params: 参数矩阵，形状 [N, n_params]
        param_names: 参数名称列表，长度 n_params
        metadata: 附加元数据字典（可选）
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with h5py.File(output_path, "w") as f:
        # 主数据集
        f.create_dataset(
            "timeseries",
            data=timeseries.astype(np.float32),
            compression="gzip",
            compression_opts=4,
        )
        f.create_dataset(
            "params",
            data=params.astype(np.float32),
            compression="gzip",
            compression_opts=4,
        )

        # 参数名称（存为字节字符串）
        f.create_dataset(
            "param_names",
            data=np.array([n.encode("utf-8") for n in param_names]),
        )

        # 元数据
        if metadata:
            meta_grp = f.create_group("metadata")
            for k, v in metadata.items():
                if isinstance(v, (int, float, str, bool)):
                    meta_grp.attrs[k] = v
                elif isinstance(v, (list, np.ndarray)):
                    meta_grp.create_dataset(k, data=np.array(v))

        # 数据集基本信息写入根属性
        f.attrs["n_samples"] = timeseries.shape[0]
        f.attrs["n_wells"] = timeseries.shape[1]
        f.attrs["n_timesteps"] = timeseries.shape[2]
        f.attrs["n_params"] = params.shape[1]


def load_dataset(
    input_path: str,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    从 HDF5 文件加载数据集。

    Returns:
        timeseries: [N, n_wells, n_timesteps]
        params: [N, n_params]
        param_names: 参数名称列表
    """
    with h5py.File(input_path, "r") as f:
        timeseries = f["timeseries"][:]
        params = f["params"][:]
        param_names = [n.decode("utf-8") for n in f["param_names"][:]]
    return timeseries, params, param_names
