"""实跑关键参数扰动，量化问题3和问题4结束时间的灵敏度。"""

from __future__ import annotations

import csv
import json

from model_core import ROOT, solve_model

PARAMETERS = {
    "D": "水分扩散系数",
    "hm": "表面对流传质系数",
    "h": "表面对流换热系数",
    "R": "半径尺度",
}
PERTURBATIONS = (-0.015, 0.015)


def drying_time(problem: int, scales: dict[str, float] | None = None) -> float:
    """用统一的中等密度网格计算结束时间，单位为h。"""

    result = solve_model(
        problem,
        7.0 * 86400.0,
        n_intervals=150,
        grid_power=2.0,
        stop_at_dry=True,
        rtol=3.0e-8,
        atol=3.0e-10,
        max_step=300.0,
        scales=scales,
    )
    if result.event_time is None:
        raise RuntimeError("扰动情景在计算范围内未达到干燥阈值")
    return result.event_time / 3600.0


def main() -> None:
    records = []
    summary = {}
    for problem in (3, 4):
        base = drying_time(problem)
        summary[f"q{problem}_base_hours"] = base
        print(f"问题{problem}基准={base:.6f} h", flush=True)
        for key, name in PARAMETERS.items():
            for ratio in PERTURBATIONS:
                value = drying_time(problem, {key: 1.0 + ratio})
                change = (value - base) / base * 100.0
                elasticity = change / (ratio * 100.0)
                record = {
                    "problem": problem,
                    "parameter": key,
                    "parameter_cn": name,
                    "perturbation": ratio,
                    "drying_time_h": value,
                    "change_percent": change,
                    "elasticity": elasticity,
                }
                records.append(record)
                print(
                    f"  {name}{ratio:+.1%}: {value:.6f} h " f"({change:+.4f}%)",
                    flush=True,
                )

    output_dir = ROOT / "results"
    with (output_dir / "sensitivity.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    (output_dir / "sensitivity.json").write_text(
        json.dumps(
            {"summary": summary, "records": records}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
