"""从正式计算结果中生成论文表格与结果摘要。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def load(problem: int):
    """读取指定问题的正式高分辨率结果。"""

    return np.load(RESULTS / f"q{problem}_base.npz")


def profile_at(data, time_s: float, positions_cm: list[float], field: str):
    """对时间和径向位置作线性插值，提取论文代表值。"""

    times = data["t"]
    right = int(np.searchsorted(times, time_s))
    if right == 0:
        values = data[field][0]
        radius = float(data["radius"][0])
    elif right >= len(times):
        values = data[field][-1]
        radius = float(data["radius"][-1])
    else:
        left = right - 1
        weight = (time_s - times[left]) / (times[right] - times[left])
        values = (1.0 - weight) * data[field][left] + weight * data[field][right]
        radius = float(
            (1.0 - weight) * data["radius"][left] + weight * data["radius"][right]
        )
    output = []
    for position in positions_cm:
        xi = min(position / (radius * 100.0), 1.0)
        output.append(float(np.interp(xi, data["x"], values)))
    return output


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    """生成紧凑的Markdown表格。"""

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def fmt(values, digits=4):
    """统一数值精度。"""

    return [f"{value:.{digits}f}" for value in values]


def main() -> None:
    q1, q2, q3, q4 = (load(i) for i in range(1, 5))
    fixed_positions = [0.0, 0.5, 1.0, 1.5, 2.0]

    sections = ["# 建模结果汇总", ""]
    sections += [
        "## 问题1：常物性热湿耦合",
        "",
        markdown_table(
            ["时间/s", "中心", "0.5 cm", "1.0 cm", "1.5 cm", "表面"],
            [
                [time] + fmt(profile_at(q1, time, fixed_positions, "temperature"))
                for time in [100, 300, 600, 900, 1200, 1500, 1800]
            ],
        ),
        "",
        "上表为温度（°C）。水分浓度如下（kg/kg）：",
        "",
        markdown_table(
            ["时间/s", "中心", "0.5 cm", "1.0 cm", "1.5 cm", "表面"],
            [
                [time] + fmt(profile_at(q1, time, fixed_positions, "moisture"))
                for time in [100, 300, 600, 900, 1200, 1500, 1800]
            ],
        ),
        "",
        "## 问题2：变物性热湿耦合",
        "",
        markdown_table(
            ["时间/h", "指标", "中心", "0.5 cm", "1.0 cm", "1.5 cm", "表面"],
            [
                [f"{hour:g}", field_label]
                + fmt(profile_at(q2, hour * 3600, fixed_positions, field))
                for hour in [1, 2, 3]
                for field, field_label in [
                    ("temperature", "温度/°C"),
                    ("moisture", "水分/(kg/kg)"),
                ]
            ],
        ),
        "",
        "## 问题3：达到干燥阈值",
        "",
        f"连续事件时刻：{float(q3['event_time']) / 3600:.6f} h；提交表末时刻：{float(q3['t'][-1]) / 3600:.6f} h。",
        "",
        markdown_table(
            ["时间/h", "中心", "0.5 cm", "1.0 cm", "1.5 cm", "表面"],
            [
                [f"{hour:g}"]
                + fmt(profile_at(q3, hour * 3600, fixed_positions, "moisture"))
                for hour in [6, 12, 18, 24, 36, 48]
            ]
            + [
                ["事件时刻"]
                + fmt(
                    profile_at(
                        q3,
                        float(q3["event_time"]),
                        fixed_positions,
                        "moisture",
                    )
                )
            ],
        ),
        "",
        "## 问题4：收缩边界",
        "",
        f"连续事件时刻：{float(q4['event_time']) / 3600:.6f} h；提交表末时刻：{float(q4['t'][-1]) / 3600:.6f} h；事件半径：{float(np.interp(float(q4['event_time']), q4['t'], q4['radius'])) * 100:.4f} cm。",
        "",
        markdown_table(
            ["时间/h", "半径/cm", "中心水分", "0.5 cm水分", "1.0 cm水分", "表面水分"],
            [
                [
                    f"{hour:g}",
                    f"{float(np.interp(hour * 3600, q4['t'], q4['radius'])) * 100:.4f}",
                ]
                + fmt(profile_at(q4, hour * 3600, [0.0, 0.5, 1.0, 2.0], "moisture"))
                for hour in [6, 12, 18, 24, 36, 48]
            ]
            + [
                [
                    "事件时刻",
                    f"{float(np.interp(float(q4['event_time']), q4['t'], q4['radius'])) * 100:.4f}",
                ]
                + fmt(
                    profile_at(
                        q4,
                        float(q4["event_time"]),
                        [0.0, 0.5, 1.0, 2.0],
                        "moisture",
                    )
                )
            ],
        ),
        "",
        "注：问题4中超过当时半径的位置自动映射为表面，仅用于本摘要；正式result4.xlsx严格按题面固定位置加动态表面输出。",
        "",
    ]

    validation = json.loads((RESULTS / "validation_summary.json").read_text("utf-8"))
    sensitivity = json.loads((RESULTS / "sensitivity.json").read_text("utf-8"))
    robustness = json.loads((RESULTS / "robustness.json").read_text("utf-8"))
    mechanism = json.loads(
        (RESULTS / "mechanism_decomposition.json").read_text("utf-8")
    )
    sections += [
        "## 数值验证与稳健性",
        "",
        "```json",
        json.dumps(
            {
                "validation": validation,
                "sensitivity": sensitivity,
                "robustness": robustness,
                "mechanism_decomposition": mechanism,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
    ]
    (ROOT / "建模结果汇总.md").write_text("\n".join(sections), encoding="utf-8")

    macros = [
        "% 本文件由generate_paper_data.py自动生成",
        f"\\newcommand{{\\QThreeEventHours}}{{{float(q3['event_time']) / 3600:.6f}}}",
        f"\\newcommand{{\\QFourEventHours}}{{{float(q4['event_time']) / 3600:.6f}}}",
        f"\\newcommand{{\\QThreeOutputSeconds}}{{{int(q3['t'][-1])}}}",
        f"\\newcommand{{\\QFourOutputSeconds}}{{{int(q4['t'][-1])}}}",
        f"\\newcommand{{\\QFourEventRadius}}{{{float(np.interp(float(q4['event_time']), q4['t'], q4['radius'])) * 100:.4f}}}",
        f"\\newcommand{{\\QTwoFinalCenterT}}{{{profile_at(q2, 10800, [0.0], 'temperature')[0]:.4f}}}",
        f"\\newcommand{{\\QTwoFinalSurfaceT}}{{{profile_at(q2, 10800, [2.0], 'temperature')[0]:.4f}}}",
        f"\\newcommand{{\\QTwoFinalCenterC}}{{{profile_at(q2, 10800, [0.0], 'moisture')[0]:.4f}}}",
        f"\\newcommand{{\\QTwoFinalSurfaceC}}{{{profile_at(q2, 10800, [2.0], 'moisture')[0]:.4f}}}",
    ]
    (ROOT / "paper_data.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
