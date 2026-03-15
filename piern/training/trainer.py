"""
模型训练器

包含训练循环、验证和早停逻辑。
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
from pathlib import Path
from typing import Dict, Optional
import json

from .metrics import compute_metrics


class Trainer:
    """
    模型训练器

    参数:
        model: PyTorch 模型
        device: 'cpu' 或 'cuda'
        learning_rate: 学习率
        weight_decay: L2 正则化系数（默认 1e-5）
    """

    def __init__(
        self,
        model: nn.Module,
        device: str = 'cpu',
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5
    ):
        self.model = model.to(device)
        self.device = device
        self.learning_rate = learning_rate

        # 优化器
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )

        # 损失函数
        self.criterion = nn.MSELoss()

        # 训练历史
        self.history = {
            'train_loss': [],
            'train_r2': [],
            'val_loss': [],
            'val_r2': [],
        }

    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        """
        训练一个 epoch

        参数:
            train_loader: 训练数据加载器

        返回:
            训练指标字典
        """
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_targets = []

        pbar = tqdm(train_loader, desc="Training", leave=False)
        for params, timeseries in pbar:
            params = params.to(self.device)
            timeseries = timeseries.to(self.device)

            # 前向传播
            pred = self.model(params)
            loss = self.criterion(pred, timeseries)

            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # 记录
            total_loss += loss.item()
            all_preds.append(pred.detach())
            all_targets.append(timeseries.detach())

            # 更新进度条
            pbar.set_postfix({'loss': loss.item()})

        # 计算整体指标
        all_preds = torch.cat(all_preds, dim=0)
        all_targets = torch.cat(all_targets, dim=0)
        metrics = compute_metrics(all_preds, all_targets)
        metrics['loss'] = total_loss / len(train_loader)

        return metrics

    def evaluate(self, val_loader: DataLoader) -> Dict[str, float]:
        """
        评估模型

        参数:
            val_loader: 验证数据加载器

        返回:
            验证指标字典
        """
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for params, timeseries in tqdm(val_loader, desc="Evaluating", leave=False):
                params = params.to(self.device)
                timeseries = timeseries.to(self.device)

                pred = self.model(params)
                loss = self.criterion(pred, timeseries)

                total_loss += loss.item()
                all_preds.append(pred)
                all_targets.append(timeseries)

        # 计算整体指标
        all_preds = torch.cat(all_preds, dim=0)
        all_targets = torch.cat(all_targets, dim=0)
        metrics = compute_metrics(all_preds, all_targets)
        metrics['loss'] = total_loss / len(val_loader)

        return metrics

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        max_epochs: int = 100,
        early_stop_r2: float = 0.90,
        patience: int = 10,
        save_path: Optional[str] = None,
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        完整训练流程

        参数:
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            max_epochs: 最大训练轮数
            early_stop_r2: 早停 R² 阈值
            patience: 早停耐心值（验证集 R² 多少轮不提升则停止）
            save_path: 模型保存路径
            verbose: 是否打印训练信息

        返回:
            最佳验证指标
        """
        best_val_r2 = -float('inf')
        best_epoch = 0
        patience_counter = 0

        for epoch in range(max_epochs):
            # 训练
            train_metrics = self.train_epoch(train_loader)

            # 验证
            val_metrics = self.evaluate(val_loader)

            # 记录历史
            self.history['train_loss'].append(train_metrics['loss'])
            self.history['train_r2'].append(train_metrics['r2'])
            self.history['val_loss'].append(val_metrics['loss'])
            self.history['val_r2'].append(val_metrics['r2'])

            # 打印信息
            if verbose:
                print(f"Epoch {epoch+1:3d}/{max_epochs} | "
                      f"Train Loss: {train_metrics['loss']:.4f} | "
                      f"Train R²: {train_metrics['r2']:.4f} | "
                      f"Val Loss: {val_metrics['loss']:.4f} | "
                      f"Val R²: {val_metrics['r2']:.4f}")

            # 检查是否达到早停条件
            if val_metrics['r2'] >= early_stop_r2:
                if verbose:
                    print(f"\n✅ 达到目标 R² >= {early_stop_r2:.2f}，停止训练")
                if save_path:
                    self.save_checkpoint(save_path, epoch, val_metrics)
                return val_metrics

            # 检查是否为最佳模型
            if val_metrics['r2'] > best_val_r2:
                best_val_r2 = val_metrics['r2']
                best_epoch = epoch
                patience_counter = 0

                # 保存最佳模型
                if save_path:
                    self.save_checkpoint(save_path, epoch, val_metrics)
            else:
                patience_counter += 1

            # 早停检查
            if patience_counter >= patience:
                if verbose:
                    print(f"\n⏹️  验证集 R² 连续 {patience} 轮未提升，停止训练")
                    print(f"   最佳 epoch: {best_epoch+1}, 最佳 R²: {best_val_r2:.4f}")
                break

        # 返回最佳验证指标
        best_metrics = {
            'loss': self.history['val_loss'][best_epoch],
            'r2': self.history['val_r2'][best_epoch],
            'epoch': best_epoch + 1
        }
        return best_metrics

    def save_checkpoint(self, save_path: str, epoch: int, metrics: Dict[str, float]):
        """保存模型检查点"""
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            'epoch': epoch + 1,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'metrics': metrics,
            'history': self.history,
        }

        torch.save(checkpoint, save_path)

        # 保存训练历史为 JSON
        history_path = save_path.with_suffix('.json')
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)

    def load_checkpoint(self, load_path: str):
        """加载模型检查点"""
        checkpoint = torch.load(load_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint.get('history', self.history)
        return checkpoint['metrics']
