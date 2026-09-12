"""依次求解A题四个问题并保存高精度中间结果。"""

from pathlib import Path
from time import perf_counter

from model_core import ROOT, save_result, solve_model


def run_one(problem: int, end: float, stop: bool, step: float, intervals: int) -> None:
    """运行单个问题并打印必要的进度信息。"""

    start = perf_counter()
    result = solve_model(
        problem,
        end,
        n_intervals=intervals,
        grid_power=2.0,
        stop_at_dry=stop,
        rtol=1.0e-9,
        atol=1.0e-11,
        max_step=30.0 if problem in (1, 2) else 180.0,
        sample_step=step,
    )
    save_result(ROOT / f"results/q{problem}_base.npz", result, problem)
    elapsed = perf_counter() - start
    end_text = (
        f"，干燥结束={result.event_time / 3600:.6f} h"
        if result.event_time is not None
        else ""
    )
    print(
        f"问题{problem}完成：{elapsed:.1f}s，nfev={result.nfev}{end_text}，"
        f"末时刻中心C={result.moisture[-1, 0]:.8f}"
    )


def main() -> None:
    """问题3、4给足四天上限，事件触发后会自动停止。"""

    Path(ROOT / "results").mkdir(parents=True, exist_ok=True)
    run_one(1, 1800.0, False, 1.0, 400)
    run_one(2, 10800.0, False, 1.0, 400)
    run_one(3, 4.0 * 86400.0, True, 60.0, 800)
    run_one(4, 4.0 * 86400.0, True, 60.0, 800)


if __name__ == "__main__":
    main()
