"""
MODFLOW 地下水位时序数据生成器。

使用 flopy 构建单层非承压含水层模型，通过参数采样批量生成
地下水位随时间变化的时序数据集。

输入参数（全部为标量，第一梯队）：
  - hk: 水力传导系数 K（m/day）
  - sy: 储水系数（无量纲）
  - pumping: 抽水量 Q（m³/day，负值）
  - strt: 初始水头（m）
  - rch: 面状补给量（m/day）

输出：
  - timeseries: [n_wells, n_timesteps] 各观测井水头时序
  - params: 当前样本的参数字典
"""

import numpy as np
import tempfile
import os
import shutil
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _get_well_positions(nrow: int, ncol: int, n_wells: int) -> list[tuple[int, int]]:
    """
    根据网格大小动态生成观测井位置。

    策略：均匀分布在网格中，避免边界和中心抽水井。
    """
    positions = []

    if n_wells == 3:
        # 3 井：左上、右上、中下
        positions = [
            (nrow // 4, ncol // 4),
            (nrow // 4, 3 * ncol // 4),
            (3 * nrow // 4, ncol // 2),
        ]
    elif n_wells == 5:
        # 5 井：四角 + 中心偏移
        positions = [
            (nrow // 4, ncol // 4),
            (nrow // 4, 3 * ncol // 4),
            (nrow // 2, ncol // 2),
            (3 * nrow // 4, ncol // 4),
            (3 * nrow // 4, 3 * ncol // 4),
        ]
    elif n_wells == 7:
        # 7 井：六边形 + 中心
        positions = [
            (nrow // 4, ncol // 4),
            (nrow // 4, ncol // 2),
            (nrow // 4, 3 * ncol // 4),
            (nrow // 2, ncol // 2),
            (3 * nrow // 4, ncol // 4),
            (3 * nrow // 4, ncol // 2),
            (3 * nrow // 4, 3 * ncol // 4),
        ]
    elif n_wells == 9:
        # 9 井：3x3 网格
        positions = [
            (nrow // 5, ncol // 5),
            (nrow // 5, ncol // 2),
            (nrow // 5, 4 * ncol // 5),
            (nrow // 2, ncol // 5),
            (nrow // 2, ncol // 2),
            (nrow // 2, 4 * ncol // 5),
            (4 * nrow // 5, ncol // 5),
            (4 * nrow // 5, ncol // 2),
            (4 * nrow // 5, 4 * ncol // 5),
        ]
    else:
        # 默认：随机分布
        for i in range(n_wells):
            r = (i + 1) * nrow // (n_wells + 1)
            c = (i % 3 + 1) * ncol // 4
            positions.append((r, c))

    # 确保所有位置都在范围内
    positions = [(min(r, nrow - 1), min(c, ncol - 1)) for r, c in positions]

    return positions


def _sample_params(cfg: Dict[str, Any], rng: np.random.Generator) -> Dict[str, float]:
    """从配置范围中均匀采样一组标量参数。"""
    p = cfg["params"]
    return {
        "hk": float(rng.uniform(p["hk_min"], p["hk_max"])),
        "sy": float(rng.uniform(p["sy_min"], p["sy_max"])),
        "pumping": float(rng.uniform(p["pumping_min"], p["pumping_max"])),
        "strt": float(rng.uniform(p["strt_min"], p["strt_max"])),
        "rch": float(rng.uniform(p["rch_min"], p["rch_max"])),
    }


def _run_modflow(
    params: Dict[str, float],
    cfg: Dict[str, Any],
    work_dir: str,
) -> np.ndarray | None:
    """
    构建并运行 MODFLOW 模型，返回观测井水头时序。

    Returns:
        水头数组，形状 [n_wells, n_timesteps]；运行失败返回 None
    """
    try:
        import flopy
    except ImportError:
        raise ImportError("请先安装 flopy：pip install flopy")

    grid = cfg["grid"]
    nrow = grid["nrow"]
    ncol = grid["ncol"]
    nlay = grid["nlay"]
    delr = grid["delr"]
    delc = grid["delc"]
    top = grid["top"]
    botm = grid["botm"]
    n_timesteps = cfg["n_timesteps"]
    n_wells = cfg["n_wells"]
    well_positions = _get_well_positions(nrow, ncol, n_wells)

    model_name = "modflow_sim"

    # --- 构建 MODFLOW-2005 模型 ---
    mf = flopy.modflow.Modflow(
        modelname=model_name,
        exe_name="mf2005",
        model_ws=work_dir,
    )

    # 离散化包（DIS）
    flopy.modflow.ModflowDis(
        mf,
        nlay=nlay,
        nrow=nrow,
        ncol=ncol,
        delr=delr,
        delc=delc,
        top=top,
        botm=botm,
        nper=n_timesteps,
        perlen=[1.0] * n_timesteps,   # 每个应力期 1 天
        nstp=[1] * n_timesteps,
        steady=[False] * n_timesteps,
    )

    # 基本包（BAS6）：初始水头
    strt = np.full((nlay, nrow, ncol), params["strt"], dtype=np.float32)
    ibound = np.ones((nlay, nrow, ncol), dtype=np.int32)
    # 四边设为常水头边界（值=-1）
    ibound[:, 0, :] = -1
    ibound[:, -1, :] = -1
    ibound[:, :, 0] = -1
    ibound[:, :, -1] = -1
    flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)

    # 层流包（LPF）
    flopy.modflow.ModflowLpf(
        mf,
        hk=params["hk"],
        sy=params["sy"],
        laytyp=1,           # 非承压层
    )

    # 补给包（RCH）：每个应力期相同补给量
    rch_data = {i: params["rch"] for i in range(n_timesteps)}
    flopy.modflow.ModflowRch(mf, rech=rch_data)

    # 井包（WEL）：中心井抽水，每个应力期相同流量
    pump_row, pump_col = nrow // 2, ncol // 2
    wel_data = {
        i: [[0, pump_row, pump_col, params["pumping"]]]
        for i in range(n_timesteps)
    }
    flopy.modflow.ModflowWel(mf, stress_period_data=wel_data)

    # 输出控制包（OC）
    flopy.modflow.ModflowOc(mf)

    # PCG 求解器
    flopy.modflow.ModflowPcg(mf)

    # 写入输入文件并运行
    mf.write_input()
    success, _ = mf.run_model(silent=True, report=False)

    if not success:
        logger.warning("MODFLOW 运行失败，跳过此样本")
        return None

    # 读取水头输出
    hds_path = os.path.join(work_dir, f"{model_name}.hds")
    if not os.path.exists(hds_path):
        logger.warning("未找到水头输出文件，跳过此样本")
        return None

    hds = flopy.utils.HeadFile(hds_path)
    # 提取各应力期水头，形状 [nlay, nrow, ncol]
    head_series = []
    for kstpkper in hds.get_kstpkper():
        head = hds.get_data(kstpkper=kstpkper)  # [nlay, nrow, ncol]
        head_series.append(head[0])              # 取第 0 层

    # head_series: list of [nrow, ncol]，长度 n_timesteps
    head_array = np.stack(head_series, axis=0)  # [n_timesteps, nrow, ncol]

    # 提取观测井位置的水头时序
    well_ts = np.zeros((len(well_positions), n_timesteps), dtype=np.float32)
    for i, (r, c) in enumerate(well_positions):
        well_ts[i] = head_array[:, r, c]

    return well_ts  # [n_wells, n_timesteps]


def generate_sample(
    cfg: Dict[str, Any],
    rng: np.random.Generator,
) -> tuple[np.ndarray, Dict[str, float]] | tuple[None, None]:
    """
    生成单个样本：采样参数 → 运行 MODFLOW → 返回时序。

    Returns:
        (timeseries [n_wells, n_timesteps], params_dict) 或 (None, None) 若失败
    """
    params = _sample_params(cfg, rng)

    with tempfile.TemporaryDirectory() as work_dir:
        ts = _run_modflow(params, cfg, work_dir)

    if ts is None:
        return None, None

    return ts, params


def generate_batch(
    cfg: Dict[str, Any],
    n_samples: int,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    批量生成 n_samples 个样本。

    Args:
        cfg: 配置字典（来自 modflow.yaml）
        n_samples: 目标样本数
        seed: 随机种子

    Returns:
        timeseries: [N, n_wells, n_timesteps]
        params_array: [N, n_params]
        param_names: 参数名称列表
    """
    from tqdm import tqdm

    rng = np.random.default_rng(seed)
    n_wells = cfg["n_wells"]
    n_timesteps = cfg["n_timesteps"]
    param_names = ["hk", "sy", "pumping", "strt", "rch"]

    ts_list = []
    params_list = []
    attempts = 0
    max_attempts = n_samples * 3  # 允许最多 3 倍失败重试

    with tqdm(total=n_samples, desc="生成 MODFLOW 样本") as pbar:
        while len(ts_list) < n_samples and attempts < max_attempts:
            ts, params = generate_sample(cfg, rng)
            attempts += 1
            if ts is None:
                continue
            ts_list.append(ts)
            params_list.append([params[k] for k in param_names])
            pbar.update(1)

    if len(ts_list) == 0:
        raise RuntimeError("所有 MODFLOW 运行均失败，请检查 mf2005 可执行文件是否在 PATH 中")

    timeseries = np.stack(ts_list, axis=0)    # [N, n_wells, n_timesteps]
    params_array = np.array(params_list)       # [N, n_params]

    logger.info(
        f"成功生成 {len(ts_list)}/{n_samples} 个样本（尝试 {attempts} 次）"
    )
    return timeseries, params_array, param_names
