"""
评估指标

包含 R²、MSE 等常用指标。
"""

import torch
from typing import Dict


def compute_mse(pred: torch.Tensor, target: torch.Tensor) -> float:
    """
    计算均方误差 (MSE)

    参数:
        pred: (batch_size, output_dim) 预测值
        target: (batch_size, output_dim) 真实值

    返回:
        MSE 值
    """
    return torch.mean((pred - target) ** 2).item()


def compute_r2(pred: torch.Tensor, target: torch.Tensor) -> float:
    """
    计算 R² 决定系数

    R² = 1 - SS_res / SS_tot
    其中:
        SS_res = Σ(y_true - y_pred)²  残差平方和
        SS_tot = Σ(y_true - y_mean)²  总平方和

    参数:
        pred: (batch_size, output_dim) 预测值
        target: (batch_size, output_dim) 真实值

    返回:
        R² 值（越接近1越好）
    """
    ss_res = torch.sum((target - pred) ** 2)
    ss_tot = torch.sum((target - target.mean()) ** 2)

    # 避免除零
    if ss_tot < 1e-8:
        return 0.0

    r2 = 1 - ss_res / ss_tot
    return r2.item()


def compute_metrics(pred: torch.Tensor, target: torch.Tensor) -> Dict[str, float]:
    """
    计算所有评估指标

    参数:
        pred: (batch_size, output_dim) 预测值
        target: (batch_size, output_dim) 真实值

    返回:
        指标字典 {'mse': ..., 'r2': ..., 'mae': ...}
    """
    metrics = {}

    # MSE
    metrics['mse'] = compute_mse(pred, target)

    # R²
    metrics['r2'] = compute_r2(pred, target)

    # MAE (平均绝对误差)
    metrics['mae'] = torch.mean(torch.abs(pred - target)).item()

    # RMSE (均方根误差)
    metrics['rmse'] = torch.sqrt(torch.tensor(metrics['mse'])).item()

    return metrics


if __name__ == "__main__":
    # 测试指标计算
    print("=" * 60)
    print("测试评估指标")
    print("=" * 60)

    # 完美预测
    target = torch.randn(100, 1825)
    pred = target.clone()
    metrics = compute_metrics(pred, target)
    print(f"\n✅ 完美预测:")
    print(f"   MSE:  {metrics['mse']:.6f}")
    print(f"   RMSE: {metrics['rmse']:.6f}")
    print(f"   MAE:  {metrics['mae']:.6f}")
    print(f"   R²:   {metrics['r2']:.6f}")

    # 随机预测
    pred = torch.randn(100, 1825)
    metrics = compute_metrics(pred, target)
    print(f"\n✅ 随机预测:")
    print(f"   MSE:  {metrics['mse']:.6f}")
    print(f"   RMSE: {metrics['rmse']:.6f}")
    print(f"   MAE:  {metrics['mae']:.6f}")
    print(f"   R²:   {metrics['r2']:.6f}")

    # 部分正确预测（加噪声）
    pred = target + torch.randn(100, 1825) * 0.1
    metrics = compute_metrics(pred, target)
    print(f"\n✅ 部分正确预测（噪声=0.1）:")
    print(f"   MSE:  {metrics['mse']:.6f}")
    print(f"   RMSE: {metrics['rmse']:.6f}")
    print(f"   MAE:  {metrics['mae']:.6f}")
    print(f"   R²:   {metrics['r2']:.6f}")
