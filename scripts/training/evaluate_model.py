#!/usr/bin/env python3
"""
模型评估脚本

用于评估已训练的模型性能。

用法:
    # 评估保存的模型
    python scripts/training/evaluate_model.py \
        --model models/mlp_baseline.pth \
        --h5-path data/modflow/baseline_groundwater_timeseries.h5

    # 可视化预测结果
    python scripts/training/evaluate_model.py \
        --model models/mlp_baseline.pth \
        --h5-path data/modflow/baseline_groundwater_timeseries.h5 \
        --visualize
"""

import argparse
import torch
from torch.utils.data import DataLoader, Subset
from pathlib import Path
import sys
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from piern.models.mlp import MLPPredictor
from piern.training.dataset import MODFLOWDataset
from piern.training.metrics import compute_metrics


def main():
    parser = argparse.ArgumentParser(description='评估训练好的模型')
    parser.add_argument('--model', type=str, required=True,
                        help='模型检查点路径')
    parser.add_argument('--h5-path', type=str, required=True,
                        help='HDF5 数据文件路径')
    parser.add_argument('--device', type=str, default='cpu',
                        help='设备（cpu/cuda）')
    parser.add_argument('--batch-size', type=int, default=256,
                        help='批量大小')
    parser.add_argument('--visualize', action='store_true',
                        help='可视化预测结果')
    parser.add_argument('--n-samples', type=int, default=5,
                        help='可视化样本数')
    args = parser.parse_args()

    print("=" * 80)
    print("📊 模型评估脚本")
    print("=" * 80)

    # 检查文件
    model_path = Path(args.model)
    h5_path = Path(args.h5_path)

    if not model_path.exists():
        print(f"❌ 模型文件不存在: {model_path}")
        sys.exit(1)

    if not h5_path.exists():
        print(f"❌ 数据文件不存在: {h5_path}")
        sys.exit(1)

    # 检查设备
    device = args.device
    if device == 'cuda' and not torch.cuda.is_available():
        print("⚠️  CUDA 不可用，切换到 CPU")
        device = 'cpu'

    print(f"✅ 模型: {model_path}")
    print(f"✅ 数据: {h5_path}")
    print(f"✅ 设备: {device}")
    print()

    # ========================================
    # 1. 加载数据
    # ========================================
    print("📁 加载数据集...")
    print("-" * 80)

    dataset = MODFLOWDataset(
        h5_path=str(h5_path),
        normalize_params=True,
        normalize_timeseries=True
    )

    data_loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0
    )

    # ========================================
    # 2. 加载模型
    # ========================================
    print("\n🧠 加载模型...")
    print("-" * 80)

    # 从检查点加载
    checkpoint = torch.load(model_path, map_location=device)

    # 推断模型架构
    input_dim = dataset.get_input_dim()
    output_dim = dataset.get_output_dim()

    model = MLPPredictor(input_dim=input_dim, output_dim=output_dim)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    print(f"   输入维度: {input_dim}")
    print(f"   输出维度: {output_dim}")
    print(f"   参数量: {model.count_parameters():,}")

    if 'epoch' in checkpoint:
        print(f"   训练轮数: {checkpoint['epoch']}")
    if 'metrics' in checkpoint:
        print(f"   保存时指标: R²={checkpoint['metrics'].get('r2', 'N/A'):.4f}")

    # ========================================
    # 3. 评估模型
    # ========================================
    print("\n📈 评估模型性能...")
    print("-" * 80)

    all_preds = []
    all_targets = []

    with torch.no_grad():
        for params, timeseries in data_loader:
            params = params.to(device)
            timeseries = timeseries.to(device)

            pred = model(params)

            all_preds.append(pred.cpu())
            all_targets.append(timeseries.cpu())

    all_preds = torch.cat(all_preds, dim=0)
    all_targets = torch.cat(all_targets, dim=0)

    # 计算指标
    metrics = compute_metrics(all_preds, all_targets)

    print(f"   MSE:  {metrics['mse']:.6f}")
    print(f"   RMSE: {metrics['rmse']:.6f}")
    print(f"   MAE:  {metrics['mae']:.6f}")
    print(f"   R²:   {metrics['r2']:.6f}")

    # ========================================
    # 4. 可视化（可选）
    # ========================================
    if args.visualize:
        print("\n📊 可视化预测结果...")
        print("-" * 80)

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("❌ 需要安装 matplotlib: pip install matplotlib")
            sys.exit(1)

        # 随机选择样本
        n_samples = min(args.n_samples, len(dataset))
        indices = np.random.choice(len(dataset), n_samples, replace=False)

        fig, axes = plt.subplots(n_samples, 1, figsize=(12, 3 * n_samples))
        if n_samples == 1:
            axes = [axes]

        for i, idx in enumerate(indices):
            params, target = dataset[idx]
            params = params.unsqueeze(0).to(device)

            with torch.no_grad():
                pred = model(params).cpu().squeeze()

            target = target.cpu().numpy()
            pred = pred.numpy()

            # 绘制
            axes[i].plot(target, label='True', alpha=0.7)
            axes[i].plot(pred, label='Pred', alpha=0.7)
            axes[i].set_title(f'Sample {idx}')
            axes[i].set_xlabel('Time')
            axes[i].set_ylabel('Value')
            axes[i].legend()
            axes[i].grid(True, alpha=0.3)

        plt.tight_layout()
        save_path = model_path.parent / f"{model_path.stem}_visualization.png"
        plt.savefig(save_path, dpi=150)
        print(f"   可视化保存至: {save_path}")

    # ========================================
    # 5. 总结
    # ========================================
    print()
    print("=" * 80)
    print("✅ 评估完成")
    print("=" * 80)

    if metrics['r2'] >= 0.85:
        print("🎉 模型性能优秀！")
    elif metrics['r2'] >= 0.70:
        print("⚠️  模型性能一般")
    else:
        print("❌ 模型性能较差")

    print(f"   R² = {metrics['r2']:.4f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
