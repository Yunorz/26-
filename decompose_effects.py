"""分离问题4中物性公式变化与半径收缩对达标时长的贡献。"""

from __future__ import annotations

import json

import numpy as np

from model_core import ROOT, solve_model


def main() -> None:
    """计算问题4物性、固定2 cm半径的反事实基准。"""

    q3 = np.load(ROOT / "results/q3_base.npz")
    q4 = np.load(ROOT / "results/q4_base.npz")
    fixed_times = {}
    for intervals in (200, 400):
        result = solve_model(
            4,
            400.0 * 3600.0,
            n_intervals=intervals,
            stop_at_dry=True,
            rtol=1.0e-7,
            atol=1.0e-9,
            max_step=600.0,
            grid_power=2.0,
            radius_function=lambda _t: 0.02,
        )
        if result.event_time is None:
            raise RuntimeError("反事实场景在计算区间内未达到阈值")
        fixed_times[str(intervals)] = result.event_time / 3600.0

    q3_hours = float(q3["event_time"]) / 3600.0
    q4_hours = float(q4["event_time"]) / 3600.0
    fixed_q4_hours = fixed_times["400"]
    summary = {
        "q3_properties_fixed_radius_hours": q3_hours,
        "q4_properties_fixed_radius_hours": fixed_q4_hours,
        "q4_properties_shrinking_radius_hours": q4_hours,
        "property_formula_contribution_hours": fixed_q4_hours - q3_hours,
        "shrinkage_contribution_hours": q4_hours - fixed_q4_hours,
        "combined_difference_hours": q4_hours - q3_hours,
        "q4_fixed_radius_grid_check_hours": fixed_times,
    }
    path = ROOT / "results/mechanism_decomposition.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
