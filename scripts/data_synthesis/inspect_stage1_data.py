"""
查看 Stage 1 数据结构
"""

import h5py
import numpy as np

h5_file = "data/modflow/groundwater_timeseries.h5"

print("=" * 70)
print("Stage 1 HDF5 文件结构")
print("=" * 70)

with h5py.File(h5_file, "r") as f:
    print(f"\n文件: {h5_file}")
    print(f"\n数据集:")
    for key in f.keys():
        dataset = f[key]
        if isinstance(dataset, h5py.Dataset):
            print(f"  - {key}: {dataset.shape} {dataset.dtype}")

    print(f"\n根属性:")
    for key in f.attrs.keys():
        print(f"  - {key}: {f.attrs[key]}")

    # 读取数据
    print(f"\n" + "=" * 70)
    print("数据内容预览")
    print("=" * 70)

    param_names = [n.decode() if isinstance(n, bytes) else n for n in f["param_names"][:]]
    params = f["params"][:]
    timeseries = f["timeseries"][:]

    print(f"\n参数名称: {param_names}")
    print(f"\n参数矩阵形状: {params.shape}")
    print(f"时序矩阵形状: {timeseries.shape}")

    print(f"\n前 3 个样本的参数:")
    for i in range(min(3, params.shape[0])):
        print(f"\n  样本 {i}:")
        for j, name in enumerate(param_names):
            print(f"    {name}: {params[i, j]:.4f}")

    print(f"\n参数统计:")
    for j, name in enumerate(param_names):
        print(f"  {name}:")
        print(f"    范围: [{params[:, j].min():.4f}, {params[:, j].max():.4f}]")
        print(f"    均值: {params[:, j].mean():.4f}")
        print(f"    标准差: {params[:, j].std():.4f}")
