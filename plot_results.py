# -*- coding: utf-8 -*-
"""生成A题论文使用的顶刊级全套学术图表（共17组，PNG 300DPI + 矢量PDF双格式）。"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from matplotlib.colors import LinearSegmentedColormap

from model_core import ROOT, material_properties

FIGURE_DIR = ROOT / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

# 学术顶刊配色定义
C_BLUE = "#2E5C8A"      # 沉稳深蓝
C_ORANGE = "#E8743B"    # 活力暖橙
C_GREEN = "#3D8B74"     # 松林雅绿
C_RED = "#C0392B"       # 警示绛红
C_CYAN = "#4A90E2"      # 天青明蓝
C_PURPLE = "#7D3C98"    # 典雅暮紫
C_GRAY = "#6E7781"      # 辅助灰
C_DARK = "#24292F"      # 文本深灰
GRID_COLOR = "#EAECEF"  # 极浅网格线

PALETTE = [C_BLUE, C_ORANGE, C_GREEN, C_RED, C_PURPLE, C_CYAN, "#E69F00"]

# 高级云图色阶（方案 A：经典顶刊雅致风，温度采用 YlOrRd 暖红，水分采用 YlGnBu 翠湖蓝）
CMAP_TEMP = "YlOrRd"
CMAP_MOIST = "YlGnBu"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimSun", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "axes.formatter.use_mathtext": True,
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 10.5,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9.5,
        "axes.linewidth": 0.9,
        "lines.linewidth": 2.0,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def save_figure(fig, name: str) -> None:
    """按竞赛要求保存高质量位图和矢量图。"""
    fig.savefig(FIGURE_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[图表生成] {name} -> PNG & PDF 完成")


def style_axis(axis) -> None:
    """精细微弱网格线，移除顶部与右侧边框。"""
    axis.grid(True, linestyle="--", linewidth=0.6, color=GRID_COLOR, alpha=0.9, zorder=0)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color("#888888")
    axis.spines["bottom"].set_color("#888888")
    axis.tick_params(colors=C_DARK, width=0.8)


def load_problem(problem: int):
    return np.load(ROOT / f"results/q{problem}_base.npz")


def read_attachment(name: str) -> np.ndarray:
    ws = openpyxl.load_workbook(
        ROOT / f"附件/{name}", data_only=True, read_only=True
    ).active
    return np.asarray(list(ws.values)[1:], dtype=float)


def field_at_position(data, field_name: str, position_cm: float) -> np.ndarray:
    values = data[field_name]
    output = []
    for profile, radius in zip(values, data["radius"]):
        x_query = position_cm / (float(radius) * 100.0)
        output.append(np.interp(x_query, data["x"], profile))
    return np.asarray(output)


def environment_figure() -> None:
    data = read_attachment("附件1.xlsx")
    t_h = data[:, 0] / 3600.0
    temp = data[:, 1]
    moist = data[:, 2]

    fig, axes = plt.subplots(2, 1, figsize=(7.6, 5.8), sharex=True)

    # 上子图：温度
    axes[0].plot(t_h, temp, color=C_ORANGE, lw=2.2, label="烘房实测温度 $T_a$", zorder=3)
    axes[0].axhline(50.0, color=C_RED, linestyle="--", lw=1.5, label="恒温设定值 50.0 °C", zorder=2)
    axes[0].fill_between(t_h, temp, 28.0, color=C_ORANGE, alpha=0.08, zorder=1)
    axes[0].set_ylabel("烘房温度 / °C", fontweight="bold", color=C_DARK)
    axes[0].legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(axes[0])

    # 下子图：水分浓度
    axes[1].plot(t_h, moist, color=C_BLUE, lw=2.2, label="烘房水分浓度 $C_a$", zorder=3)
    axes[1].axhline(0.05, color=C_GREEN, linestyle="--", lw=1.5, label="恒湿设定值 0.050 kg/kg", zorder=2)
    axes[1].fill_between(t_h, moist, 0.015, color=C_BLUE, alpha=0.08, zorder=1)
    axes[1].set_xlabel("烘干时间 / h", fontweight="bold", color=C_DARK)
    axes[1].set_ylabel("水分浓度 / (kg/kg)", fontweight="bold", color=C_DARK)
    axes[1].legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(axes[1])

    fig.suptitle("烘房环境温湿度时序演化与边界接续", fontweight="bold", fontsize=13)
    fig.tight_layout()
    save_figure(fig, "fig01_烘房环境边界")


def radius_figure() -> None:
    data = read_attachment("附件2.xlsx")
    t_h = data[:, 0] / 3600.0
    radius = data[:, 1]

    fig, ax = plt.subplots(figsize=(7.6, 4.5))

    ax.plot(t_h, radius, color=C_BLUE, lw=2.4, label="实测药材半径 $R(t)$ 曲线", zorder=3)
    ax.scatter(
        t_h[::10],
        radius[::10],
        color=C_ORANGE,
        edgecolor="white",
        linewidth=1.2,
        s=38,
        zorder=4,
        label="实测采样点",
    )
    ax.axhline(1.200, color=C_RED, linestyle="--", lw=1.5, label="收缩极限 $R \\approx 1.20$ cm", zorder=2)

    ax.set_xlabel("烘干时间 / h", fontweight="bold")
    ax.set_ylabel("药材截面半径 / cm", fontweight="bold")
    ax.set_title("药材截面半径随时间收缩的动力学历程", fontweight="bold")
    ax.set_ylim(1.05, 2.10)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig02_半径收缩曲线")
def q1_temp_contour() -> None:
    """问题1预热阶段药材内部温度时空分布云图（参考图配色与等温线样式）"""
    data = load_problem(1)
    t_grid = data["t"]
    dist_cm = data["x"] * 2.0
    t_full = data["temperature"].T  # 形状: (401, 1801)

    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    T_mesh, R_mesh = np.meshgrid(t_grid, dist_cm)

    cnt = ax.contourf(T_mesh, R_mesh, t_full, levels=30, cmap="YlOrRd")
    cbar = fig.colorbar(cnt, ax=ax)
    cbar.set_label("药材温度 / °C", fontweight="bold", fontsize=11)

    # 叠加等温线与标签
    lines = ax.contour(
        T_mesh,
        R_mesh,
        t_full,
        levels=[29, 30, 31, 32, 33, 34, 35, 36],
        colors="k",
        alpha=0.35,
        linewidths=1.0,
    )
    positions = [
        (600, 1.25),
        (850, 1.05),
        (1050, 1.05),
        (1250, 1.05),
        (1420, 1.15),
        (1560, 1.35),
        (1650, 1.65),
        (1740, 1.80),
    ]
    ax.clabel(lines, inline=True, fontsize=9, fmt="%.0f°C", manual=positions)

    ax.set_xlabel("时间 / s", fontweight="bold", fontsize=12)
    ax.set_ylabel("到药材中心距离 / cm", fontweight="bold", fontsize=12)
    ax.set_title("图3 问题1 预热平衡阶段药材内部温度时空分布云图", fontweight="bold", fontsize=13)
    fig.tight_layout()
    save_figure(fig, "fig03_问题1温度云图")


def q1_moisture_profiles() -> None:
    """问题1预热平衡阶段不同径向层位水分浓度演变历程（5条层位折线）"""
    data = load_problem(1)
    t_grid = data["t"]
    c_full = data["moisture"].T  # 形状: (401, 1801)
    dist_cm = data["x"] * 2.0

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    target_dists = [0.0, 0.5, 1.0, 1.5, 2.0]
    colors = ["#2E5C8A", "#56B4E9", "#70AD47", "#E8743B", "#D9534F"]

    for d, c in zip(target_dists, colors):
        idx = int(np.argmin(abs(dist_cm - d)))
        lbl = (
            r"中心 $r=0\ \mathrm{cm}$"
            if d == 0.0
            else (
                r"表面 $r=2.0\ \mathrm{cm}$"
                if d == 2.0
                else f"$r={d}\\ \\mathrm{{cm}}$"
            )
        )
        ax.plot(t_grid, c_full[idx, :], color=c, lw=2.2, label=lbl)

    ax.set_xlabel("时间 / s", fontweight="bold", fontsize=12)
    ax.set_ylabel("水分浓度 / (kg/kg)", fontweight="bold", fontsize=12)
    ax.set_title("图4 问题1 预热平衡阶段不同径向层位水分浓度演变历程", fontweight="bold", fontsize=13)
    ax.grid(True, linestyle="--", color="#E5E5E5", alpha=0.7)
    ax.legend(loc="lower left", frameon=True, facecolor="white", fontsize=10.5)
    fig.tight_layout()
    save_figure(fig, "fig04_问题1水分云图")


def heatmap(problem: int, field_name: str, name: str, title: str, unit: str) -> None:
    data = load_problem(problem)
    stride = 2 if problem == 1 else 15
    time_h = data["t"][::stride] / 3600.0
    radius_cm = data["x"] * 2.0
    field = data[field_name][::stride]

    is_temp = "temp" in field_name.lower()
    cmap = CMAP_TEMP if is_temp else CMAP_MOIST

    fig, ax = plt.subplots(figsize=(7.6, 4.8))

    mesh = ax.pcolormesh(
        time_h, radius_cm, field.T, shading="gouraud", cmap=cmap, rasterized=True, zorder=1
    )

    bar = fig.colorbar(mesh, ax=ax, pad=0.025, fraction=0.045)
    bar.set_label(unit, fontweight="bold", fontsize=10.5)
    bar.outline.set_edgecolor("#CCCCCC")
    bar.outline.set_linewidth(0.8)

    ax.set_xlabel("烘干时间 / h", fontweight="bold")
    ax.set_ylabel("距药材中心位置 / cm", fontweight="bold")
    ax.set_title(title, fontweight="bold")
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, name)


def profile_pair(problem: int, times: list[float], name: str, title: str) -> None:
    data = load_problem(problem)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    radius_cm = data["x"] * 2.0
    use_hours = max(times) >= 3600.0

    colors = [
        "#1F77B4", "#2CA02C", "#FF7F0E", "#D62728", "#9467BD", "#8C564B", "#E377C2"
    ][: len(times)]

    for index, time in enumerate(times):
        row = int(np.argmin(abs(data["t"] - time)))
        label = f"{time / 3600:.2g} h" if use_hours else f"{time:.0f} s"
        c = colors[index % len(colors)]
        axes[0].plot(radius_cm, data["temperature"][row], color=c, lw=1.9, label=label)
        axes[1].plot(radius_cm, data["moisture"][row], color=c, lw=1.9, label=label)

    axes[0].set_xlabel("距中心物理距离 / cm", fontweight="bold")
    axes[0].set_ylabel("温度 / °C", fontweight="bold")
    axes[0].set_title("(a) 径向温度剖面演化", fontsize=11, fontweight="bold")

    axes[1].set_xlabel("距中心物理距离 / cm", fontweight="bold")
    axes[1].set_ylabel("水分浓度 / (kg/kg)", fontweight="bold")
    axes[1].set_title("(b) 径向水分浓度剖面演化", fontsize=11, fontweight="bold")

    for ax in axes:
        style_axis(ax)

    # 提取统一图例放置在两子图上方的独立居中区域，彻底避免遮挡数据曲线
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.92),
        ncol=len(times),
        fontsize=9.2,
        frameon=True,
        facecolor="white",
        edgecolor="#D0D0D0",
    )

    fig.suptitle(title, fontweight="bold", fontsize=12.5, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    save_figure(fig, name)


def q2_moisture_surface_3d() -> None:
    """问题2 3小时烘干期水分浓度三维时空演化曲面（高保真三维立体动力学视角）"""
    data = load_problem(2)
    t_grid = data["t"] / 3600.0  # 转化为小时
    dist_cm = data["x"] * 2.0     # 径向物理距离 cm
    c_full = data["moisture"].T   # 形状: (401, 10801)

    # 抽样加速网格渲染并保持极高平滑度
    t_sub = t_grid[::60]
    c_sub = c_full[:, ::60]
    T_mesh, R_mesh = np.meshgrid(t_sub, dist_cm)

    fig = plt.figure(figsize=(9.2, 5.5))
    ax = fig.add_subplot(111, projection="3d")

    surf = ax.plot_surface(
        T_mesh, R_mesh, c_sub, cmap="viridis", edgecolor="none", alpha=0.92
    )
    cbar = fig.colorbar(surf, ax=ax, shrink=0.6, aspect=12)
    cbar.set_label("水分浓度 / (kg/kg)", fontsize=10.5, fontweight="bold")

    ax.set_xlabel("时间 / h", labelpad=9, fontsize=11, fontweight="bold")
    ax.set_ylabel("径向距离 / cm", labelpad=9, fontsize=11, fontweight="bold")
    ax.set_zlabel("水分浓度 / (kg/kg)", labelpad=9, fontsize=11, fontweight="bold")
    ax.set_title("问题2 3小时烘干期水分浓度三维时空演化曲面", fontsize=12.5, fontweight="bold")
    ax.view_init(elev=28, azim=-120)
    fig.tight_layout()
    save_figure(fig, "fig08b_问题2三维水分曲面")


def q3_profiles() -> None:
    data = load_problem(3)
    times = [6, 12, 24, 36, 48, float(data["event_time"]) / 3600.0]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    colors = [C_BLUE, "#1F968B", "#73D055", "#FDE725", C_ORANGE, C_RED]
    for index, hour in enumerate(times):
        row = int(np.argmin(abs(data["t"] - hour * 3600.0)))
        is_last = index == len(times) - 1
        label = f"达标终止时刻 ($t^* = {hour:.2f}$ h)" if is_last else f"{hour:g} h"
        ax.plot(
            data["x"] * 2.0,
            data["moisture"][row],
            color=colors[index % len(colors)],
            lw=2.5 if is_last else 1.8,
            linestyle="-" if not is_last else "-.",
            label=label,
            zorder=4 if is_last else 2,
        )

    ax.axhline(0.15, color=C_RED, linestyle="--", lw=1.8, label="全域干燥阈值 0.15 kg/kg", zorder=3)

    ax.set_xlabel("距中心径向距离 / cm", fontweight="bold")
    ax.set_ylabel("水分浓度 / (kg/kg)", fontweight="bold")
    ax.set_title("问题3（固定截面）各时刻径向水分剖面衰减演变", fontweight="bold")
    ax.legend(ncol=2, fontsize=8.5, frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig09_问题3水分剖面")


def time_history(problem: int, name: str, title: str) -> None:
    data = load_problem(problem)
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    positions = [0.0, 0.5, 1.0]

    pos_colors = [C_BLUE, C_GREEN, C_PURPLE]
    for index, position in enumerate(positions):
        values = field_at_position(data, "moisture", position)
        ax.plot(
            data["t"] / 3600.0,
            values,
            color=pos_colors[index],
            lw=2.0,
            label=f"径向位置 $r = {position:g}$ cm",
        )
    ax.plot(
        data["t"] / 3600.0,
        data["moisture"][:, -1],
        color=C_ORANGE,
        lw=2.0,
        linestyle="--",
        label="药材外表面 ($r = R$)",
    )
    ax.axhline(0.15, color=C_RED, linestyle=":", lw=1.8, label="干燥阈值 0.15 kg/kg")

    ax.set_xlabel("烘干时间 / h", fontweight="bold")
    ax.set_ylabel("水分浓度 / (kg/kg) [对数刻度]", fontweight="bold")
    ax.set_title(title, fontweight="bold")
    ax.set_yscale("log")
    ax.legend(ncol=2, fontsize=8.5, loc="upper right", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, name)


def q4_profiles() -> None:
    data = load_problem(4)
    times = [6, 12, 24, 36, 48, float(data["event_time"]) / 3600.0]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    colors = [C_BLUE, "#1F968B", "#73D055", "#FDE725", C_ORANGE, C_RED]
    for index, hour in enumerate(times):
        row = int(np.argmin(abs(data["t"] - hour * 3600.0)))
        radius_cm = data["x"] * data["radius"][row] * 100.0
        is_last = index == len(times) - 1
        label = f"达标终止时刻 ($t^* = {hour:.2f}$ h)" if is_last else f"{hour:g} h"
        ax.plot(
            radius_cm,
            data["moisture"][row],
            color=colors[index % len(colors)],
            lw=2.5 if is_last else 1.8,
            linestyle="-" if not is_last else "-.",
            label=label,
            zorder=4 if is_last else 2,
        )

    ax.axhline(0.15, color=C_RED, linestyle="--", lw=1.8, label="全域干燥阈值 0.15 kg/kg", zorder=3)
    ax.set_xlabel("距药材中心的实际物理距离 / cm", fontweight="bold")
    ax.set_ylabel("水分浓度 / (kg/kg)", fontweight="bold")
    ax.set_title("问题4（收缩动边界）真实物理尺度下的水分剖面演化", fontweight="bold")
    ax.legend(ncol=2, fontsize=8.5, frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig11_问题4水分剖面")


def model_comparison() -> None:
    q3 = load_problem(3)
    q4 = load_problem(4)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))

    # 左图：中心水分衰减对比
    axes[0].plot(q3["t"] / 3600.0, q3["moisture"][:, 0], color=C_BLUE, lw=2.2, label="问题3（固定半径 2 cm）")
    axes[0].plot(q4["t"] / 3600.0, q4["moisture"][:, 0], color=C_ORANGE, lw=2.2, label="问题4（实测动态收缩半径）")
    axes[0].axhline(0.15, color=C_RED, linestyle="--", lw=1.5, label="干燥目标阈值 0.15")
    axes[0].set_xlabel("烘干时间 / h", fontweight="bold")
    axes[0].set_ylabel("中心水分浓度 / (kg/kg)", fontweight="bold")
    axes[0].set_title("(a) 中心水分浓度衰减历程对比", fontsize=11, fontweight="bold")
    axes[0].legend(frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(axes[0])

    # 右图：达标时长对比柱状图
    t3 = float(q3["event_time"]) / 3600.0
    t4 = float(q4["event_time"]) / 3600.0
    bars = axes[1].bar(
        ["问题3 (固定半径)", "问题4 (动态收缩)"],
        [t3, t4],
        color=[C_BLUE, C_ORANGE],
        width=0.48,
        edgecolor="white",
        linewidth=1.2,
        zorder=3,
    )
    axes[1].set_ylabel("烘干达标时刻 / h", fontweight="bold")
    axes[1].set_ylim(0, 68)
    axes[1].set_title("(b) 烘干所需总时长对比", fontsize=11, fontweight="bold")

    for b, val in zip(bars, [t3, t4]):
        axes[1].text(
            b.get_x() + b.get_width() / 2,
            val + 1.2,
            f"{val:.2f} h",
            ha="center",
            fontweight="bold",
            fontsize=10,
            color=C_DARK,
        )
    style_axis(axes[1])

    fig.suptitle("几何收缩对药材热风烘干动力学进程的宏观影响", fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    save_figure(fig, "fig13_固定与收缩模型比较")


def convergence_figure() -> None:
    report = json.loads((ROOT / "results/validation_summary.json").read_text("utf-8"))
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    official = {"q3": 57.472601409555914, "q4": 51.087244916844185}

    markers = ["o", "s"]
    colors = [C_BLUE, C_ORANGE]
    for index, key in enumerate(("q3", "q4")):
        values = report["event_time_hours_by_grid"][key]
        nodes = np.asarray([int(item) for item in values] + [800])
        hours = np.asarray([values[item] for item in values] + [official[key]])
        lbl = "问题3 (固定半径)" if key == "q3" else "问题4 (收缩半径)"
        ax.plot(
            nodes,
            hours,
            marker=markers[index],
            markersize=6.5,
            markerfacecolor="white",
            markeredgewidth=1.8,
            markeredgecolor=colors[index],
            color=colors[index],
            lw=2.0,
            label=lbl,
            zorder=3,
        )

    ax.set_xlabel("径向有限体积加密区间数 $N$", fontweight="bold")
    ax.set_ylabel("达标烘干时长 / h", fontweight="bold")
    ax.set_title("有限体积网格加密下的达标时刻单调收敛性（二阶表观阶）", fontweight="bold")
    ax.legend(frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig14_网格收敛")


def sensitivity_figure() -> None:
    data = json.loads((ROOT / "results/sensitivity.json").read_text("utf-8"))["records"]
    labels = ["水分扩散系数 $D$", "对流传质系数 $h_m$", "对流换热系数 $h$", "药材半径 $R$"]
    param_keys = ["水分扩散系数", "表面对流传质系数", "表面对流换热系数", "半径尺度"]

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), sharey=True)

    for axis, problem, p_title in zip(axes, (3, 4), ("(a) 问题3 敏感性响应", "(b) 问题4 敏感性响应")):
        rows = [item for item in data if item["problem"] == problem]
        negative = [
            next(
                item["change_percent"]
                for item in rows
                if item["parameter_cn"] == key and item["perturbation"] < 0
            )
            for key in param_keys
        ]
        positive = [
            next(
                item["change_percent"]
                for item in rows
                if item["parameter_cn"] == key and item["perturbation"] > 0
            )
            for key in param_keys
        ]
        y = np.arange(len(labels))
        b1 = axis.barh(y - 0.17, negative, height=0.32, color=C_BLUE, edgecolor="white", label="参数 -1.5%", zorder=3)
        b2 = axis.barh(y + 0.17, positive, height=0.32, color=C_ORANGE, edgecolor="white", label="参数 +1.5%", zorder=3)
        axis.axvline(0.0, color="#333333", linewidth=1.0, zorder=4)

        axis.set_yticks(y, labels)
        axis.set_xlabel("达标烘干时长相对变化 / %", fontweight="bold")
        axis.set_title(p_title, fontsize=11, fontweight="bold")
        axis.set_xlim(-3.6, 3.6)
        style_axis(axis)

    axes[1].legend(loc="lower right", fontsize=9, frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    fig.suptitle("关键控制参数 ±1.5% 扰动对烘干时长的影响灵敏度", fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    save_figure(fig, "fig15_参数灵敏度")


def robustness_figure() -> None:
    data = json.loads((ROOT / "results/robustness.json").read_text("utf-8"))
    scenarios = [
        "线性插值与名义恒温值",
        "线性插值与末次实测值",
        "线性插值与末小时均值",
    ]
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    x = np.arange(len(scenarios))
    width = 0.32

    for offset, problem, color, lbl in [
        (-width / 2, 3, C_BLUE, "问题3 时长偏差"),
        (width / 2, 4, C_ORANGE, "问题4 时长偏差"),
    ]:
        rows = [item for item in data if item["problem"] == problem]
        values = [
            next(item["difference_min"] for item in rows if item["scenario"] == name)
            for name in scenarios
        ]
        bars = ax.bar(x + offset, values, width=width, color=color, edgecolor="white", label=lbl, zorder=3)

    ax.axhline(0.0, color="#333333", linewidth=1.0, zorder=4)
    ax.set_xticks(
        x, ["线性插值\n名义恒温接续", "末次实测噪声值\n永久外推接续", "末一小时均值\n平滑外推接续"]
    )
    ax.set_ylabel("相对基准达标时间的偏差 / min", fontweight="bold")
    ax.set_title("不同边界插值与接续策略下的模型求解稳健性检验", fontweight="bold")
    ax.set_ylim(-21, 5)
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig16_边界口径稳健性")


def diffusivity_figure() -> None:
    concentration = np.linspace(0.05, 2.55, 500)
    temperature = np.full_like(concentration, 50.0)
    fig, ax = plt.subplots(figsize=(7.6, 4.6))

    styles = [
        (1, "问题1经验式 $D(C)$", C_BLUE, "-"),
        (3, "问题2—3耦合式 $D(C, 50^\circ\mathrm{C})$", C_ORANGE, "-"),
        (4, "问题4经验式 $D(C, 50^\circ\mathrm{C})$", C_GREEN, "--"),
    ]

    for problem, label, color, ls in styles:
        diffusivity = material_properties(problem, concentration, temperature)[3]
        ax.semilogy(concentration, diffusivity, color=color, lw=2.2, linestyle=ls, label=label, zorder=3)

    ax.axvline(0.15, color=C_RED, linestyle="--", lw=1.8, label="干燥终止阈值 0.15 kg/kg", zorder=4)

    ax.set_xlabel("药材干基水分浓度 $C$ / (kg/kg)", fontweight="bold")
    ax.set_ylabel(r"水分扩散系数 $D$ / (m$^2$/s) [对数刻度]", fontweight="bold")
    ax.set_title("各问题水分扩散系数随浓度非线性衰减的机理特征", fontweight="bold")
    ax.legend(loc="lower right", frameon=True, facecolor="white", edgecolor="#E0E0E0", framealpha=0.9)
    style_axis(ax)
    fig.tight_layout()
    save_figure(fig, "fig17_扩散系数机理")


def main() -> None:
    print(">>> 开始批量渲染顶刊级学术图表...")
    environment_figure()
    radius_figure()
    q1_temp_contour()
    q1_moisture_profiles()
    profile_pair(
        1,
        [100, 300, 600, 900, 1200, 1500, 1800],
        "fig05_问题1径向剖面",
        "问题1预热阶段各采样时刻的径向温湿状态剖面",
    )
    heatmap(2, "temperature", "fig06_问题2温度云图", "问题2变物性耦合下内部温度场时空演化", "温度 / °C")
    heatmap(
        2,
        "moisture",
        "fig07_问题2水分云图",
        "问题2变物性耦合下内部水分浓度场时空演化",
        "水分浓度 / (kg/kg)",
    )
    profile_pair(
        2,
        [1800, 3600, 5400, 7200, 9000, 10800],
        "fig08_问题2径向剖面",
        "问题2三小时内热湿耦合径向剖面动态演变",
    )
    q2_moisture_surface_3d()
    q3_profiles()
    time_history(3, "fig10_问题3水分历程", "问题3固定截面模型各径向测点水分浓度衰减历程")
    q4_profiles()
    time_history(4, "fig12_问题4水分历程", "问题4收缩动边界模型各径向测点水分浓度衰减历程")
    model_comparison()
    convergence_figure()
    sensitivity_figure()
    robustness_figure()
    diffusivity_figure()
    print(">>> 18 组顶刊级图表全部渲染完成，覆盖 PNG 与 PDF！")


if __name__ == "__main__":
    main()
