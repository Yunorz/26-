"""对A题求解器执行网格、容差、守恒和解析特例验证。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid
from scipy.optimize import brentq
from scipy.special import j0, j1

from model_core import (
    C0,
    H_MASS,
    R0,
    ROOT,
    T0_C,
    load_environment,
    solve_model,
)


def cylinder_roots(biot: float, count: int = 50) -> np.ndarray:
    """扫描求解无限圆柱第三类边界的特征根。"""

    def equation(value: float) -> float:
        return value * j1(value) - biot * j0(value)

    grid = np.linspace(1.0e-8, (count + 8) * np.pi, (count + 8) * 80)
    values = equation(grid)
    roots: list[float] = []
    for left, right, f_left, f_right in zip(
        grid[:-1], grid[1:], values[:-1], values[1:]
    ):
        if f_left * f_right < 0.0:
            root = brentq(equation, left, right)
            if not roots or abs(root - roots[-1]) > 1.0e-8:
                roots.append(root)
        if len(roots) >= count:
            break
    return np.asarray(roots)


def analytical_temperature(x: np.ndarray, time: float, air: float) -> np.ndarray:
    """计算恒定环境下常物性无限圆柱的解析级数解。"""

    conductivity = 0.36
    alpha = conductivity / (820.0 * 2600.0)
    biot = 25.0 * R0 / conductivity
    roots = cylinder_roots(biot)
    coeff = 2.0 * j1(roots) / (roots * (j0(roots) ** 2 + j1(roots) ** 2))
    theta = np.sum(
        coeff[:, None]
        * j0(roots[:, None] * x[None, :])
        * np.exp(-(roots**2)[:, None] * alpha * time / R0**2),
        axis=0,
    )
    return air + (T0_C - air) * theta


def control_volume_weights(x: np.ndarray) -> np.ndarray:
    """返回与主程序一致的无量纲环形控制体权重。"""

    west = np.empty_like(x)
    east = np.empty_like(x)
    west[0] = 0.0
    west[1:] = 0.5 * (x[:-1] + x[1:])
    east[:-1] = west[1:]
    east[-1] = 1.0
    return 0.5 * (east**2 - west**2)


def conservation_residual(problem: int) -> float:
    """检查半离散水分方程的整体通量平衡。"""

    data = np.load(ROOT / f"results/q{problem}_base.npz")
    time = data["t"]
    radius = data["radius"]
    moisture = data["moisture"]
    weight = control_volume_weights(data["x"])
    inventory = moisture @ weight
    _, c_air = load_environment()
    boundary = np.asarray([c_air(float(t)) for t in time])
    rate = H_MASS * (boundary - moisture[:, -1]) / radius
    predicted = trapezoid(rate, time)
    observed = inventory[-1] - inventory[0]
    return float(abs(observed - predicted) / max(abs(observed), 1.0e-15))


def event_convergence(problem: int) -> dict[str, float]:
    """比较径向网格加密后的干燥结束时刻。"""

    values: dict[str, float] = {}
    for n in (100, 200, 400):
        result = solve_model(
            problem,
            7.0 * 86400.0,
            n_intervals=n,
            grid_power=2.0,
            stop_at_dry=True,
            rtol=1.0e-8,
            atol=1.0e-10,
            max_step=300.0,
        )
        if result.event_time is None:
            raise RuntimeError(f"问题{problem}在计算区间内未达到干燥阈值")
        values[str(n)] = result.event_time / 3600.0
    return values


def main() -> None:
    """汇总全部验证并保存机器可读结果。"""

    constant_env = (lambda _t: 50.0, lambda _t: C0)
    numerical = solve_model(
        1,
        3600.0,
        n_intervals=400,
        rtol=1.0e-9,
        atol=1.0e-11,
        max_step=30.0,
        sample_step=600.0,
        environment=constant_env,
    )
    analytical_errors = {}
    for index, time in enumerate(numerical.t[1:], start=1):
        exact = analytical_temperature(numerical.x, float(time), 50.0)
        analytical_errors[str(int(time))] = float(
            np.max(np.abs(numerical.temperature[index] - exact))
        )

    isolated = solve_model(
        1,
        3600.0,
        n_intervals=50,
        scales={"h": 0.0, "hm": 0.0},
        sample_step=600.0,
    )
    isolation_error = max(
        float(np.max(np.abs(isolated.temperature - T0_C))),
        float(np.max(np.abs(isolated.moisture - C0))),
    )

    convergence = {"q3": event_convergence(3), "q4": event_convergence(4)}
    tolerance = {}
    for problem in (3, 4):
        loose = solve_model(
            problem,
            7.0 * 86400.0,
            n_intervals=200,
            grid_power=2.0,
            stop_at_dry=True,
            rtol=1.0e-6,
            atol=1.0e-8,
            max_step=300.0,
        )
        tight = solve_model(
            problem,
            7.0 * 86400.0,
            n_intervals=200,
            grid_power=2.0,
            stop_at_dry=True,
            rtol=1.0e-8,
            atol=1.0e-10,
            max_step=300.0,
        )
        tolerance[f"q{problem}"] = abs(loose.event_time - tight.event_time) / 3600.0

    trends = {}
    for problem in (1, 2, 3, 4):
        data = np.load(ROOT / f"results/q{problem}_base.npz")
        temp_diff = np.diff(data["temperature"], axis=1)
        moisture_diff = np.diff(data["moisture"], axis=1)
        trends[f"q{problem}"] = {
            "temperature_radial_violation": float(max(0.0, -temp_diff.min())),
            "moisture_radial_violation": float(max(0.0, moisture_diff.max())),
            "moisture_min": float(data["moisture"].min()),
            "moisture_max": float(data["moisture"].max()),
        }

    report = {
        "analytic_heat_max_abs_error_C": analytical_errors,
        "zero_transfer_max_abs_error": isolation_error,
        "event_time_hours_by_grid": convergence,
        "event_time_tolerance_difference_hours": tolerance,
        "moisture_balance_relative_residual": {
            f"q{problem}": conservation_residual(problem) for problem in (1, 2, 3, 4)
        },
        "physical_trends": trends,
    }
    output = ROOT / "results/validation_summary.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
