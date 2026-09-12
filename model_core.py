"""A题热湿耦合模型的公共求解器。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import openpyxl
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parent
R0 = 0.02
H_HEAT = 25.0
H_MASS = 8.0e-7
T0_C = 28.0
C0 = 2.55


@dataclass
class ModelResult:
    """保存一次计算的网格、场量和结束信息。"""

    t: np.ndarray
    x: np.ndarray
    radius: np.ndarray
    temperature: np.ndarray
    moisture: np.ndarray
    event_time: float | None
    nfev: int
    njev: int


def _read_numeric_xlsx(path: Path) -> np.ndarray:
    """读取附件中的纯数值表，不改动原文件。"""

    ws = openpyxl.load_workbook(path, data_only=True, read_only=True).active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    return np.asarray(rows, dtype=float)


def load_environment() -> tuple[Callable[[float], float], Callable[[float], float]]:
    """构造烘房温度和水分浓度的连续边界函数。"""

    data = _read_numeric_xlsx(ROOT / "附件/附件1.xlsx")
    time = data[:, 0]
    temp = PchipInterpolator(time, data[:, 1], extrapolate=False)
    moisture = PchipInterpolator(time, data[:, 2], extrapolate=False)
    t_end = float(time[-1])

    def t_air(t: float) -> float:
        if t <= t_end:
            return float(temp(max(t, 0.0)))
        return 50.0

    def c_air(t: float) -> float:
        if t <= t_end:
            return float(moisture(max(t, 0.0)))
        return 0.05

    return t_air, c_air


def load_radius() -> Callable[[float], float]:
    """构造问题4使用的单调收缩半径函数，返回值单位为m。"""

    data = _read_numeric_xlsx(ROOT / "附件/附件2.xlsx")
    time = data[:, 0]
    radius_m = data[:, 1] / 100.0
    interp = PchipInterpolator(time, radius_m, extrapolate=False)
    t_end = float(time[-1])
    r_end = float(radius_m[-1])

    def radius(t: float) -> float:
        if t <= t_end:
            return float(interp(max(t, 0.0)))
        return r_end

    return radius


def material_properties(
    problem: int,
    moisture: np.ndarray,
    temperature_c: np.ndarray,
    scales: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """按题面经验式计算节点物性。"""

    scales = scales or {}
    c = np.maximum(moisture, 1.0e-8)
    tk = np.maximum(temperature_c + 273.15, 1.0)

    if problem == 1:
        rho = np.full_like(c, 820.0)
        cp = np.full_like(c, 2600.0)
        conductivity = np.full_like(c, 0.36)
        diffusivity = 7.0e-9 * np.exp(-0.89 / c)
    elif problem in (2, 3):
        rho = 650.0 + 128.0 * c
        cp = 1450.0 + 2736.0 * c / (c + 1.0)
        conductivity = 0.21 + 0.38 * c / (c + 1.0)
        diffusivity = 2.4e-3 * np.exp(-0.45 / c) * np.exp(-3850.0 / tk)
    elif problem == 4:
        rho = 760.0 + 90.0 * c
        cp = 1850.0 + 2150.0 * c / (c + 1.0)
        conductivity = 0.12 + 0.20 * c / (c + 1.0)
        diffusivity = 4.2e-4 * np.exp(-0.30 / c) * np.exp(-3850.0 / tk)
    else:
        raise ValueError(f"未知问题编号：{problem}")

    rho *= scales.get("rho", 1.0)
    cp *= scales.get("cp", 1.0)
    conductivity *= scales.get("k", 1.0)
    diffusivity *= scales.get("D", 1.0)
    return rho, cp, conductivity, diffusivity


def _harmonic_mean(values: np.ndarray) -> np.ndarray:
    """计算相邻节点物性的调和平均，保证界面通量连续。"""

    left = values[:-1]
    right = values[1:]
    return 2.0 * left * right / np.maximum(left + right, 1.0e-30)


def _jacobian_sparsity(n_nodes: int):
    """给BDF提供局部耦合结构，降低长时间计算开销。"""

    size = 2 * n_nodes
    pattern = lil_matrix((size, size), dtype=int)
    for field in range(2):
        offset = field * n_nodes
        for i in range(n_nodes):
            lo = max(0, i - 1)
            hi = min(n_nodes, i + 2)
            pattern[offset + i, offset + lo : offset + hi] = 1
            other = (1 - field) * n_nodes
            pattern[offset + i, other + lo : other + hi] = 1
    return pattern.tocsr()


def solve_model(
    problem: int,
    t_end: float,
    n_intervals: int = 100,
    stop_at_dry: bool = False,
    rtol: float = 1.0e-7,
    atol: float = 1.0e-9,
    max_step: float = 300.0,
    scales: dict[str, float] | None = None,
    sample_step: float | None = None,
    environment: (
        tuple[Callable[[float], float], Callable[[float], float]] | None
    ) = None,
    grid_power: float = 1.0,
    radius_function: Callable[[float], float] | None = None,
) -> ModelResult:
    """求解指定问题；问题4自动启用收缩半径。"""

    t_air, c_air = environment if environment is not None else load_environment()
    radius_scale = (scales or {}).get("R", 1.0)
    if problem == 4:
        base_radius_fun = (
            radius_function if radius_function is not None else load_radius()
        )
        radius_fun = lambda t: radius_scale * base_radius_fun(t)
    else:
        radius_fun = lambda _t: radius_scale * R0
    n_nodes = n_intervals + 1
    if grid_power < 1.0:
        raise ValueError("grid_power必须不小于1")
    uniform = np.linspace(0.0, 1.0, n_nodes)
    x = 1.0 - (1.0 - uniform) ** grid_power
    west = np.empty(n_nodes)
    east = np.empty(n_nodes)
    west[0] = 0.0
    west[1:] = 0.5 * (x[:-1] + x[1:])
    east[:-1] = west[1:]
    east[-1] = 1.0
    volume = 0.5 * (east**2 - west**2)
    face_x = 0.5 * (x[:-1] + x[1:])
    node_spacing = np.diff(x)

    heat_transfer = H_HEAT * (scales or {}).get("h", 1.0)
    mass_transfer = H_MASS * (scales or {}).get("hm", 1.0)

    def rhs(t: float, state: np.ndarray) -> np.ndarray:
        temp = state[:n_nodes]
        moisture = state[n_nodes:]
        rho, cp, conductivity, diffusivity = material_properties(
            problem, moisture, temp, scales
        )
        radius = radius_fun(t)

        k_face = _harmonic_mean(conductivity)
        d_face = _harmonic_mean(diffusivity)
        heat_flux = face_x * k_face * np.diff(temp) / node_spacing
        mass_flux = face_x * d_face * np.diff(moisture) / node_spacing

        heat_balance = np.empty(n_nodes)
        mass_balance = np.empty(n_nodes)
        heat_balance[0] = heat_flux[0]
        mass_balance[0] = mass_flux[0]
        heat_balance[1:-1] = heat_flux[1:] - heat_flux[:-1]
        mass_balance[1:-1] = mass_flux[1:] - mass_flux[:-1]
        heat_balance[-1] = (
            radius * heat_transfer * (t_air(t) - temp[-1]) - heat_flux[-1]
        )
        mass_balance[-1] = (
            radius * mass_transfer * (c_air(t) - moisture[-1]) - mass_flux[-1]
        )

        dtemp = heat_balance / (rho * cp * radius**2 * volume)
        dmoisture = mass_balance / (radius**2 * volume)
        return np.concatenate((dtemp, dmoisture))

    def dry_event(_t: float, state: np.ndarray) -> float:
        return float(np.max(state[n_nodes:]) - 0.15)

    dry_event.direction = -1
    dry_event.terminal = True

    initial = np.concatenate((np.full(n_nodes, T0_C), np.full(n_nodes, C0)))
    solution = solve_ivp(
        rhs,
        (0.0, t_end),
        initial,
        method="BDF",
        dense_output=True,
        events=dry_event if stop_at_dry else None,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
        jac_sparsity=_jacobian_sparsity(n_nodes),
    )
    if not solution.success:
        raise RuntimeError(solution.message)

    event_time = None
    if stop_at_dry and solution.t_events[0].size:
        event_time = float(solution.t_events[0][0])
        actual_end = event_time
    else:
        actual_end = float(solution.t[-1])

    if sample_step is None:
        times = solution.t
    else:
        times = np.arange(0.0, actual_end + 1.0e-8, sample_step)
        if times[-1] < actual_end - 1.0e-8:
            times = np.append(times, actual_end)
    sampled = solution.sol(times)
    radius = np.asarray([radius_fun(float(t)) for t in times])
    return ModelResult(
        t=times,
        x=x,
        radius=radius,
        temperature=sampled[:n_nodes].T,
        moisture=sampled[n_nodes:].T,
        event_time=event_time,
        nfev=solution.nfev,
        njev=solution.njev,
    )


def save_result(path: Path, result: ModelResult, problem: int) -> None:
    """把高精度计算结果保存为可复算的压缩数组。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        problem=problem,
        t=result.t,
        x=result.x,
        radius=result.radius,
        temperature=result.temperature,
        moisture=result.moisture,
        event_time=np.nan if result.event_time is None else result.event_time,
        nfev=result.nfev,
        njev=result.njev,
    )


def interpolate_profile(
    values: np.ndarray, x_grid: np.ndarray, radius_m: float, positions_cm: np.ndarray
) -> np.ndarray:
    """把归一化网格上的场量插值到实际径向位置。"""

    x_query = positions_cm / (radius_m * 100.0)
    if np.any(x_query > 1.0 + 1.0e-10):
        raise ValueError("请求的位置已经越过药材表面")
    return np.interp(np.clip(x_query, 0.0, 1.0), x_grid, values)
