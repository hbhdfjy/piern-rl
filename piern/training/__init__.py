"""
训练工具模块

包含数据加载、训练循环和评估指标。
"""

from .dataset import MODFLOWDataset
from .trainer import Trainer
from .metrics import compute_r2, compute_mse

__all__ = ['MODFLOWDataset', 'Trainer', 'compute_r2', 'compute_mse']
