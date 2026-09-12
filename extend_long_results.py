"""把问题3、4的结果延长到事件后的首个整60秒时刻。"""

import math

import numpy as np

from model_core import ROOT, save_result, solve_model


def extend(problem: int) -> None:
    """保留连续事件时刻，同时生成严格60秒间隔的完整输出。"""

    old = np.load(ROOT / f"results/q{problem}_base.npz")
    event_time = float(old["event_time"])
    output_end = math.ceil(event_time / 60.0) * 60.0
    result = solve_model(
        problem,
        output_end,
        n_intervals=800,
        grid_power=2.0,
        stop_at_dry=False,
        rtol=1.0e-9,
        atol=1.0e-11,
        max_step=180.0,
        sample_step=60.0,
    )
    result.event_time = event_time
    save_result(ROOT / f"results/q{problem}_base.npz", result, problem)
    print(
        f"问题{problem}延长到{output_end:.0f}s；末时刻全域最大C="
        f"{result.moisture[-1].max():.8f}"
    )


def main() -> None:
    for problem in (3, 4):
        extend(problem)


if __name__ == "__main__":
    main()
