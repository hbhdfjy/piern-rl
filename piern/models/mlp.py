"""
轻量级 MLP 模型用于参数到时序预测

用于验证 2.5M 数据集的可用性。
"""

import torch
import torch.nn as nn
from typing import List


class MLPPredictor(nn.Module):
    """
    多层感知机 (MLP) 用于参数到时序预测

    架构：
        Input: param_dim 维参数
        Hidden: 可配置的隐藏层（默认 [64, 128, 64]）
        Output: output_dim 维时序数据（n_wells × n_timesteps）

    参数:
        input_dim: 输入参数维度（取决于场景，如 baseline=5, land_subsidence=13）
        output_dim: 输出时序维度（n_wells × n_timesteps，如 5×365=1825）
        hidden_dims: 隐藏层维度列表
        dropout: Dropout 概率（默认 0.2）

    示例:
        >>> model = MLPPredictor(input_dim=5, output_dim=1825)
        >>> params = torch.randn(32, 5)  # batch_size=32
        >>> timeseries = model(params)   # (32, 1825)
    """

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_dims: List[int] = None,
        dropout: float = 0.2
    ):
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [64, 128, 64]

        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dims = hidden_dims
        self.dropout = dropout

        # 构建网络层
        layers = []
        prev_dim = input_dim

        for i, hidden_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            # 最后一层隐藏层不加 Dropout
            if i < len(hidden_dims) - 1:
                layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim

        # 输出层（无激活函数）
        layers.append(nn.Linear(prev_dim, output_dim))

        self.network = nn.Sequential(*layers)

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        """Xavier 初始化"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        参数:
            x: (batch_size, input_dim) 输入参数

        返回:
            (batch_size, output_dim) 预测的时序数据
        """
        return self.network(x)

    def count_parameters(self) -> int:
        """统计模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


if __name__ == "__main__":
    # 测试模型
    print("=" * 60)
    print("测试 MLPPredictor")
    print("=" * 60)

    # 创建模型（baseline 场景：5个输入参数，5口井×365天=1825输出）
    model = MLPPredictor(input_dim=5, output_dim=1825)
    print(f"✅ 模型创建成功")
    print(f"   输入维度: {model.input_dim}")
    print(f"   输出维度: {model.output_dim}")
    print(f"   隐藏层: {model.hidden_dims}")
    print(f"   参数量: {model.count_parameters():,}")

    # 测试前向传播
    batch_size = 32
    x = torch.randn(batch_size, 5)
    y = model(x)
    print(f"\n✅ 前向传播测试")
    print(f"   输入形状: {x.shape}")
    print(f"   输出形状: {y.shape}")

    # 测试不同配置
    print(f"\n" + "=" * 60)
    print("测试不同场景配置")
    print("=" * 60)

    scenarios = [
        ("baseline", 5, 1825),
        ("land_subsidence", 13, 1825),
        ("multilayer_5layers", 8, 1825),
    ]

    for name, input_dim, output_dim in scenarios:
        model = MLPPredictor(input_dim=input_dim, output_dim=output_dim)
        print(f"✅ {name:25s} | 输入={input_dim:2d} | 输出={output_dim:4d} | 参数={model.count_parameters():,}")
