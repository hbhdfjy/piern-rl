"""
PyTorch Dataset 用于加载 MODFLOW HDF5 数据
"""

import torch
from torch.utils.data import Dataset
import h5py
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


class MODFLOWDataset(Dataset):
    """
    加载 MODFLOW HDF5 数据集

    HDF5 文件结构:
        - parameters: (N, param_dim) - 输入参数
        - timeseries: (N, n_wells, n_timesteps) - 输出时序
        - metadata: 场景元数据

    参数:
        h5_path: HDF5 文件路径
        normalize_params: 是否归一化参数（默认 True）
        normalize_timeseries: 是否归一化时序（默认 True）

    示例:
        >>> dataset = MODFLOWDataset("data/modflow/baseline_groundwater_timeseries.h5")
        >>> params, timeseries = dataset[0]
        >>> print(params.shape, timeseries.shape)  # (5,), (1825,)
    """

    def __init__(
        self,
        h5_path: str,
        normalize_params: bool = True,
        normalize_timeseries: bool = True
    ):
        self.h5_path = Path(h5_path)
        if not self.h5_path.exists():
            raise FileNotFoundError(f"HDF5 文件不存在: {h5_path}")

        # 加载数据到内存（避免多进程访问 HDF5 的问题）
        with h5py.File(h5_path, 'r') as f:
            # 尝试两种可能的键名
            if 'parameters' in f:
                self.params = f['parameters'][:]
            elif 'params' in f:
                self.params = f['params'][:]
            else:
                raise KeyError(f"未找到参数数据，可用键: {list(f.keys())}")

            self.timeseries = f['timeseries'][:]  # (N, n_wells, n_timesteps)

            # 读取元数据
            self.metadata = {}
            if 'metadata' in f:
                for key in f['metadata'].attrs:
                    self.metadata[key] = f['metadata'].attrs[key]

        # 展平时序维度 (N, n_wells, n_timesteps) -> (N, n_wells * n_timesteps)
        N, n_wells, n_timesteps = self.timeseries.shape
        self.timeseries = self.timeseries.reshape(N, n_wells * n_timesteps)

        # 归一化
        self.normalize_params = normalize_params
        self.normalize_timeseries = normalize_timeseries

        if normalize_params:
            self.params_mean = self.params.mean(axis=0)
            self.params_std = self.params.std(axis=0) + 1e-8
            self.params = (self.params - self.params_mean) / self.params_std

        if normalize_timeseries:
            self.timeseries_mean = self.timeseries.mean(axis=0)
            self.timeseries_std = self.timeseries.std(axis=0) + 1e-8
            self.timeseries = (self.timeseries - self.timeseries_mean) / self.timeseries_std

        # 转换为 PyTorch tensors
        self.params = torch.from_numpy(self.params).float()
        self.timeseries = torch.from_numpy(self.timeseries).float()

        print(f"✅ 数据集加载成功: {self.h5_path.name}")
        print(f"   样本数: {len(self)}")
        print(f"   参数维度: {self.params.shape[1]}")
        print(f"   时序维度: {self.timeseries.shape[1]} ({n_wells} wells × {n_timesteps} timesteps)")
        print(f"   参数归一化: {normalize_params}")
        print(f"   时序归一化: {normalize_timeseries}")

    def __len__(self) -> int:
        return len(self.params)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        返回:
            params: (param_dim,) 输入参数
            timeseries: (n_wells * n_timesteps,) 输出时序
        """
        return self.params[idx], self.timeseries[idx]

    def get_input_dim(self) -> int:
        """返回输入参数维度"""
        return self.params.shape[1]

    def get_output_dim(self) -> int:
        """返回输出时序维度"""
        return self.timeseries.shape[1]


if __name__ == "__main__":
    # 测试数据集加载
    import sys
    from pathlib import Path

    # 查找 baseline 数据文件
    data_dir = Path(__file__).parent.parent.parent / "data" / "modflow"
    h5_files = list(data_dir.glob("*.h5"))

    if not h5_files:
        print("❌ 未找到 HDF5 数据文件")
        sys.exit(1)

    print("=" * 60)
    print("测试 MODFLOWDataset")
    print("=" * 60)

    for h5_file in h5_files[:3]:  # 只测试前3个文件
        print(f"\n📁 {h5_file.name}")
        print("-" * 60)

        try:
            dataset = MODFLOWDataset(str(h5_file))

            # 测试读取单个样本
            params, timeseries = dataset[0]
            print(f"   样本0: params={params.shape}, timeseries={timeseries.shape}")

            # 测试批量读取
            indices = [0, 1, 2]
            batch_params = torch.stack([dataset[i][0] for i in indices])
            batch_timeseries = torch.stack([dataset[i][1] for i in indices])
            print(f"   批量读取: params={batch_params.shape}, timeseries={batch_timeseries.shape}")

        except Exception as e:
            print(f"   ❌ 加载失败: {e}")
