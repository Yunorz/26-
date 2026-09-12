"""比较边界插值、恒温取值和半径插值口径的稳健性。"""

from __future__ import annotations

import csv
import json

import numpy as np
from scipy.interpolate import interp1d

from model_core import ROOT, _read_numeric_xlsx, load_environment, solve_model


def linear_environment(final_temperature: float, final_moisture: float):
    """构造线性插值环境边界，并指定恒温阶段取值。"""

    data = _read_numeric_xlsx(ROOT / "附件/附件1.xlsx")
    t_end = float(data[-1, 0])
    temp = interp1d(data[:, 0], data[:, 1], kind="linear")
    moisture = interp1d(data[:, 0], data[:, 2], kind="linear")

    def t_air(t: float) -> float:
        return float(temp(t)) if t <= t_end else final_temperature

    def c_air(t: float) -> float:
        return float(moisture(t)) if t <= t_end else final_moisture

    return t_air, c_air


def linear_radius():
    """构造附件2的分段线性半径函数。"""

    data = _read_numeric_xlsx(ROOT / "附件/附件2.xlsx")
    time = data[:, 0]
    radius = data[:, 1] / 100.0
    interpolation = interp1d(time, radius, kind="linear")

    def radius_fun(t: float) -> float:
        if t <= time[-1]:
            return float(interpolation(t))
        return float(radius[-1])

    return radius_fun


def run(problem: int, environment=None, radius_function=None) -> float:
    """用一致的中等密度网格计算稳健性情景。"""

    result = solve_model(
        problem,
        7.0 * 86400.0,
        n_intervals=150,
        grid_power=2.0,
        stop_at_dry=True,
        rtol=3.0e-8,
        atol=3.0e-10,
        max_step=300.0,
        environment=environment,
        radius_function=radius_function,
    )
    if result.event_time is None:
        raise RuntimeError("稳健性情景未达到干燥阈值")
    return result.event_time / 3600.0


def main() -> None:
    pchip_environment = load_environment()
    scenarios = [
        ("基准PCHIP与名义恒温值", pchip_environment, None),
        ("线性插值与名义恒温值", linear_environment(50.0, 0.05), None),
        ("线性插值与末次实测值", linear_environment(50.165, 0.04986), None),
        ("线性插值与末小时均值", linear_environment(49.9989, 0.04999), None),
    ]
    records = []
    for problem in (3, 4):
        base = run(problem, pchip_environment)
        for name, environment, radius_function in scenarios:
            value = run(problem, environment, radius_function)
            records.append(
                {
                    "problem": problem,
                    "scenario": name,
                    "drying_time_h": value,
                    "difference_min": (value - base) * 60.0,
                }
            )
            print(
                f"问题{problem} {name}: {value:.6f} h，"
                f"偏差{(value-base)*60:+.3f} min",
                flush=True,
            )
        if problem == 4:
            value = run(problem, pchip_environment, linear_radius())
            records.append(
                {
                    "problem": problem,
                    "scenario": "半径改用线性插值",
                    "drying_time_h": value,
                    "difference_min": (value - base) * 60.0,
                }
            )
            print(
                f"问题4 半径改用线性插值: {value:.6f} h，"
                f"偏差{(value-base)*60:+.3f} min",
                flush=True,
            )

    output_dir = ROOT / "results"
    with (output_dir / "robustness.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    (output_dir / "robustness.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
