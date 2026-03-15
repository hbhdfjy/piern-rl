#!/usr/bin/env python3
"""
单场景训练脚本

用于验证 2.5M 数据集可用性的最小可行训练管线。

用法:
    # 使用默认配置训练 baseline 场景
    python scripts/training/train_single_scenario.py

    # 指定配置文件
    python scripts/training/train_single_scenario.py --config configs/training/mlp_baseline.yaml

    # 指定数据文件
    python scripts/training/train_single_scenario.py --h5-path data/modflow/land_subsidence_timeseries.h5

    # 使用 GPU
    python scripts/training/train_single_scenario.py --device cuda
"""

import argparse
import yaml
import torch
from torch.utils.data import DataLoader, random_split
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from piern.models.mlp import MLPPredictor
from piern.training.dataset import MODFLOWDataset
from piern.training.trainer import Trainer


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='训练单场景 MLP 模型')
    parser.add_argument('--config', type=str, default='configs/training/mlp_baseline.yaml',
                        help='配置文件路径')
    parser.add_argument('--h5-path', type=str, default=None,
                        help='HDF5 数据文件路径（覆盖配置文件）')
    parser.add_argument('--device', type=str, default=None,
                        help='设备（cpu/cuda，覆盖配置文件）')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='批量大小（覆盖配置文件）')
    parser.add_argument('--max-epochs', type=int, default=None,
                        help='最大训练轮数（覆盖配置文件）')
    args = parser.parse_args()

    # 加载配置
    print("=" * 80)
    print("🚀 单场景训练脚本")
    print("=" * 80)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    cfg = load_config(config_path)
    print(f"✅ 加载配置: {config_path}")

    # 命令行参数覆盖
    if args.h5_path:
        cfg['data']['h5_path'] = args.h5_path
    if args.device:
        cfg['device'] = args.device
    if args.batch_size:
        cfg['training']['batch_size'] = args.batch_size
    if args.max_epochs:
        cfg['training']['max_epochs'] = args.max_epochs

    # 检查数据文件
    h5_path = Path(cfg['data']['h5_path'])
    if not h5_path.exists():
        print(f"❌ 数据文件不存在: {h5_path}")
        print(f"   请先运行数据生成脚本生成数据")
        sys.exit(1)

    # 检查设备
    device = cfg['device']
    if device == 'cuda' and not torch.cuda.is_available():
        print("⚠️  CUDA 不可用，切换到 CPU")
        device = 'cpu'

    print(f"   设备: {device}")
    print(f"   数据文件: {h5_path}")
    print()

    # ========================================
    # 1. 加载数据
    # ========================================
    print("📁 加载数据集...")
    print("-" * 80)

    dataset = MODFLOWDataset(
        h5_path=str(h5_path),
        normalize_params=cfg['data']['normalize_params'],
        normalize_timeseries=cfg['data']['normalize_timeseries']
    )

    # 划分训练/验证集
    train_ratio = cfg['data']['train_ratio']
    train_size = int(train_ratio * len(dataset))
    val_size = len(dataset) - train_size

    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    print(f"   训练集: {len(train_dataset)} 样本")
    print(f"   验证集: {len(val_dataset)} 样本")
    print()

    # 创建数据加载器
    batch_size = cfg['training']['batch_size']
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # 避免多进程问题
        pin_memory=(device == 'cuda')
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(device == 'cuda')
    )

    # ========================================
    # 2. 创建模型
    # ========================================
    print("🧠 创建模型...")
    print("-" * 80)

    input_dim = dataset.get_input_dim()
    output_dim = dataset.get_output_dim()

    model = MLPPredictor(
        input_dim=input_dim,
        output_dim=output_dim,
        hidden_dims=cfg['model']['hidden_dims'],
        dropout=cfg['model']['dropout']
    )

    print(f"   输入维度: {input_dim}")
    print(f"   输出维度: {output_dim}")
    print(f"   隐藏层: {cfg['model']['hidden_dims']}")
    print(f"   参数量: {model.count_parameters():,}")
    print(f"   样本-参数比: {len(dataset) / model.count_parameters():.2f}")
    print()

    # ========================================
    # 3. 训练模型
    # ========================================
    print("🏋️  开始训练...")
    print("-" * 80)

    trainer = Trainer(
        model=model,
        device=device,
        learning_rate=cfg['training']['learning_rate'],
        weight_decay=cfg['training']['weight_decay']
    )

    # 保存路径
    save_dir = Path(cfg['save']['model_dir'])
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / cfg['save']['model_name']

    # 训练
    best_metrics = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        max_epochs=cfg['training']['max_epochs'],
        early_stop_r2=cfg['training']['early_stop_r2'],
        patience=cfg['training']['patience'],
        save_path=str(save_path),
        verbose=True
    )

    # ========================================
    # 4. 总结
    # ========================================
    print()
    print("=" * 80)
    print("✅ 训练完成")
    print("=" * 80)
    print(f"   最佳验证 R²: {best_metrics['r2']:.4f}")
    print(f"   最佳验证 Loss: {best_metrics['loss']:.4f}")
    print(f"   最佳 Epoch: {best_metrics['epoch']}")
    print(f"   模型保存至: {save_path}")

    if cfg['save']['save_history']:
        history_path = save_path.with_suffix('.json')
        print(f"   训练历史: {history_path}")

    # 判断是否成功
    if best_metrics['r2'] >= 0.85:
        print()
        print("🎉 验证成功！数据集可用于训练")
        print(f"   R² = {best_metrics['r2']:.4f} >= 0.85")
    elif best_metrics['r2'] >= 0.70:
        print()
        print("⚠️  部分成功，但 R² 较低")
        print(f"   R² = {best_metrics['r2']:.4f} < 0.85")
        print("   建议：增加训练轮数或调整模型架构")
    else:
        print()
        print("❌ 训练效果不佳")
        print(f"   R² = {best_metrics['r2']:.4f} < 0.70")
        print("   可能原因：数据质量问题、模型容量不足、学习率不当")

    print("=" * 80)


if __name__ == "__main__":
    main()
