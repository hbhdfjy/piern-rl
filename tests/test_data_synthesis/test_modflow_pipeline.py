"""
MODFLOW 数据合成框架单元测试。

测试策略：用 mock 替换 flopy 运行，专注测试管线逻辑。
"""

import numpy as np
import os
import tempfile
import pytest

from data_synthesis.augmenters.perturbation import (
    apply_identity,
    apply_scaling,
    apply_offset,
    augment_dataset,
    PerturbationType,
)
from data_synthesis.validators.quality_filter import filter_sample, filter_dataset
from data_synthesis.utils.hdf5_writer import save_dataset, load_dataset


# ──────────────────────────────────────────────
# 辅助：构造假数据
# ──────────────────────────────────────────────

def _make_fake_data(N=10, n_wells=5, n_t=365, seed=0):
    rng = np.random.default_rng(seed)
    ts = rng.normal(5.0, 1.0, size=(N, n_wells, n_t)).astype(np.float32)
    params = rng.uniform(0, 1, size=(N, 5)).astype(np.float32)
    return ts, params


_VAL_CFG = {
    "max_nan_ratio": 0.05,
    "min_variance": 1e-6,
    "max_head_value": 15.0,
    "min_head_value": -5.0,
}

_AUG_CFG = {
    "identity_ratio": 0.4,
    "scaling_ratio": 0.3,
    "offset_ratio": 0.3,
    "scaling_k_min": 0.8,
    "scaling_k_max": 1.2,
    "offset_b_std": 0.1,
}


# ──────────────────────────────────────────────
# 测试：扰动增强
# ──────────────────────────────────────────────

class TestPerturbation:

    def test_identity_unchanged(self):
        ts, params = _make_fake_data(N=4)
        ts_out, p_out = apply_identity(ts, params)
        np.testing.assert_array_equal(ts_out, ts)
        np.testing.assert_array_equal(p_out, params)

    def test_identity_is_copy(self):
        ts, params = _make_fake_data(N=4)
        ts_out, _ = apply_identity(ts, params)
        ts_out[0, 0, 0] = 9999.0
        assert ts[0, 0, 0] != 9999.0, "identity 应返回副本，不应修改原数据"

    def test_scaling_shape(self):
        ts, params = _make_fake_data(N=6)
        ts_out, p_out = apply_scaling(ts, params)
        assert ts_out.shape == ts.shape
        assert p_out.shape == params.shape

    def test_scaling_range(self):
        ts, params = _make_fake_data(N=100)
        rng = np.random.default_rng(42)
        ts_out, _ = apply_scaling(ts, params, k_min=0.9, k_max=1.1, rng=rng)
        # 缩放后每个位置的比值应在 [0.9, 1.1] 内
        ratio = ts_out / (ts + 1e-9)
        assert ratio.min() >= 0.89
        assert ratio.max() <= 1.11

    def test_offset_shape(self):
        ts, params = _make_fake_data(N=6)
        ts_out, p_out = apply_offset(ts, params)
        assert ts_out.shape == ts.shape
        assert p_out.shape == params.shape

    def test_offset_params_unchanged(self):
        ts, params = _make_fake_data(N=6)
        _, p_out = apply_offset(ts, params)
        np.testing.assert_array_equal(p_out, params)

    def test_augment_dataset_total_size(self):
        ts, params = _make_fake_data(N=10)
        aug_ts, aug_params, aug_types = augment_dataset(ts, params, _AUG_CFG)
        # 增强后总样本数应等于原始样本数
        assert aug_ts.shape[0] == ts.shape[0]
        assert aug_params.shape[0] == params.shape[0]
        assert len(aug_types) == ts.shape[0]

    def test_augment_dataset_type_labels(self):
        ts, params = _make_fake_data(N=20)
        _, _, aug_types = augment_dataset(ts, params, _AUG_CFG)
        valid_types = {PerturbationType.IDENTITY, PerturbationType.SCALING, PerturbationType.OFFSET}
        for t in aug_types:
            assert t in valid_types


# ──────────────────────────────────────────────
# 测试：质量过滤
# ──────────────────────────────────────────────

class TestQualityFilter:

    def test_normal_sample_passes(self):
        rng = np.random.default_rng(0)
        ts = rng.normal(5.0, 1.0, size=(5, 365)).astype(np.float32)
        assert filter_sample(ts, _VAL_CFG) is True

    def test_nan_sample_fails(self):
        ts = np.full((5, 365), np.nan, dtype=np.float32)
        assert filter_sample(ts, _VAL_CFG) is False

    def test_constant_sample_fails(self):
        ts = np.full((5, 365), 5.0, dtype=np.float32)
        assert filter_sample(ts, _VAL_CFG) is False

    def test_out_of_range_sample_fails(self):
        ts = np.full((5, 365), 100.0, dtype=np.float32)  # 超过 max_head_value=15
        assert filter_sample(ts, _VAL_CFG) is False

    def test_filter_dataset_keeps_valid(self):
        ts, params = _make_fake_data(N=10)
        # 前 3 个样本设为 NaN（应被过滤）
        ts[:3] = np.nan
        ts_out, p_out, mask = filter_dataset(ts, params, _VAL_CFG)
        assert ts_out.shape[0] == 7
        assert p_out.shape[0] == 7
        assert mask.sum() == 7


# ──────────────────────────────────────────────
# 测试：HDF5 存储
# ──────────────────────────────────────────────

class TestHDF5Writer:

    def test_save_and_load_roundtrip(self):
        ts, params = _make_fake_data(N=8, n_wells=5, n_t=100)
        param_names = ["hk", "sy", "pumping", "strt", "rch"]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.h5")
            save_dataset(path, ts, params, param_names)
            ts_loaded, params_loaded, names_loaded = load_dataset(path)

        np.testing.assert_allclose(ts_loaded, ts, atol=1e-5)
        np.testing.assert_allclose(params_loaded, params, atol=1e-5)
        assert names_loaded == param_names

    def test_output_shapes(self):
        ts, params = _make_fake_data(N=5, n_wells=3, n_t=50)
        param_names = ["a", "b", "c", "d", "e"]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.h5")
            save_dataset(path, ts, params, param_names)
            ts_loaded, params_loaded, _ = load_dataset(path)

        assert ts_loaded.shape == (5, 3, 50)
        assert params_loaded.shape == (5, 5)
