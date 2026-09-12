# 竞赛

> **项目说明**：本项目建立了圆柱状药材在对流热风烘房环境下的**一维径向非线性热湿耦合扩散与移动收缩边界（Stefan型移动边界）数学物理模型**。
> 本仓库为精简高保真版本，专供代码审阅、学术交流及网页端大语言模型（GPT/Claude等）极速读取与理解。

---

## 目录索引 (Repository Structure)

```text
.
├── README.md                      # [当前文件] 项目全景导引与核心结论速查（GPT首选读取文件）
├── 题目分析报告.md                 # 赛题物理背景、量纲分析、红线约束与模型推导深度剖析
├── 建模结果汇总.md                 # 问题1~4的全部定量时空分布、阶段节点与关键物理指标汇总
├── AI自查终审报告.md               # 竞赛合规性自查、去AIGC特征终审与交叉验证报告
├── 交叉审阅记录.md                 # 建模与计算过程中团队交叉审查记录与修正要点
├── 术语表格.md                     # 统一数学物理符号、量纲、物理含义与取值对照表
├── A题.pdf                        # 全国大学生数学建模竞赛 A题赛题原题
├── AI工具使用详情.pdf              # 竞赛AI工具使用合规披露报告
├── paper_data.tex                 # 论文数据宏定义（供 LaTeX 自动化引用核心计算结果）
│
├── paper/                         # 论文成果
│   ├── main.tex                   # 完整学术论文 LaTeX 源码（包含推导、算法、图表与讨论）
│   ├── main.pdf                   # 最终编译生成的完整学术论文 PDF
│   ├── ai_usage.tex / .pdf        # AI工具使用说明 LaTeX 源码及成品 PDF
│   └── support_file_list.tex      # 支撑材料文件清单 LaTeX
│
├── figures/                       # 论文全部正式高清插图 (矢量 PDF + 预览 PNG)
│   ├── fig01_烘房环境边界         # 烘房实测温湿度历程及 4h 后的稳态过渡
│   ├── fig02_半径收缩曲线         # 药材外半径随时间的单调收缩动力学曲线
│   ├── fig03 ~ fig05              # 问题1：温度/水分云图与径向剖面分布
│   ├── fig06 ~ fig08b             # 问题2：温度/水分演化云图与三维水分曲面
│   ├── fig09 ~ fig10              # 问题3：长程干燥水分剖面与特征位历程
│   ├── fig11 ~ fig12              # 问题4：动边界收缩下的水分剖面与历程
│   ├── fig13                      # 固定边界与收缩边界干燥动力学机制对比
│   └── fig14 ~ fig17              # 网格收敛性、灵敏度、边界稳健性与机理分解
│
├── results/                       # 关键量化指标、统计分析与提交结果
│   ├── analytic_error_metrics.json# 解析解对比与守恒律验证指标
│   ├── mechanism_decomposition.json# 传热传质主导机制效应分解
│   ├── sensitivity.json / .csv    # 关键物性参数全局与局部灵敏度指标
│   ├── robustness.json / .csv     # 边界条件扰动下的模型稳健性测试指标
│   ├── validation_summary.json    # 数值离散精度与守恒检验汇总
│   ├── xlsx_validation.json       # 导出数据格式、维度与物理单调性校验
│   └── result1.xlsx ~ result4.xlsx# 严格按照赛题规范填充的最终提交数据表格
│
├── 附件/                          # 赛题原始输入数据与官方模板
│   ├── 附件1.xlsx                  # 烘房环境温度与水分浓度时序监测数据 (0~4h)
│   ├── 附件2.xlsx                  # 药材实测半径变化时序数据 (0~72h)
│   └── 附件3/                     # 竞赛官方提供的四个空白结果提交模板
│
└── 核心计算脚本 (Python 3.10+)
    ├── model_core.py              # 核心物理模型：变物性参数方程、移动网格有限体积离散与求解引擎
    ├── solve_all.py               # 主执行脚本：一键串联运行问题1至问题4并生成基准数据
    ├── export_results.py          # 结果格式化导出模块：按赛题要求规范写入 result1~4.xlsx
    ├── validate_model.py          # 严谨性验证：数值收敛阶、解析解对比及守恒律检验
    ├── verify_results.py          # 提交结果自检脚本：检查空值、物理上下界与单调性
    ├── sensitivity_analysis.py    # 灵敏度分析：物性扰动对干燥速率及特征指标的影响
    ├── robustness_analysis.py     # 稳健性分析：测试测量噪声与边界插值扰动
    ├── decompose_effects.py       # 效应分解：定量测算物性非线性与边界收缩对干燥的贡献
    ├── plot_results.py            # 全套科研级论文插图绘图脚本（Matplotlib）
    ├── generate_paper_data.py     # 自动化提取数值并生成 paper_data.tex 宏
    └── extend_long_results.py     # 长周期连续模拟与阈值精确事件捕获
```

---

## 核心数学物理模型概述

### 1. 物理几何简化
药材样品为圆柱体，长 $L = 25\ \text{cm}$，初始半径 $R_0 = 2\ \text{cm}$。长径比为 $6.25$，两端端面面积仅占侧面积的 $8\%$。由于端部效应微弱且题目统一考察“到药材中心的距离”，模型简化为**一维径向轴对称非定常传热传质问题**，坐标 $r \in [0, R(t)]$。

### 2. 传热与传质控制方程
在圆柱坐标系下，内部温度场 $T(r,t)$ 和干基含水率（水分浓度）$C(r,t)$ 满足耦合抛物型偏微分方程：

$$
\rho(C) c_p(C) \frac{\partial T}{\partial t} = \frac{1}{r} \frac{\partial}{\partial r} \left( r k(C) \frac{\partial T}{\partial r} \right)
$$

$$
\frac{\partial C}{\partial t} = \frac{1}{r} \frac{\partial}{\partial r} \left( r D(C,T) \frac{\partial C}{\partial r} \right)
$$

- **对称中心边界 ($r=0$)**：
  $$\left.\frac{\partial T}{\partial r}\right|_{r=0} = 0, \quad \left.\frac{\partial C}{\partial r}\right|_{r=0} = 0$$
- **对流外表面边界 ($r=R(t)$)**：
  $$\left. k(C) \frac{\partial T}{\partial r} \right|_{r=R} = h \, [T_\infty(t) - T(R,t)]$$
  $$\left. D(C,T) \frac{\partial C}{\partial r} \right|_{r=R} = h_m \, [C_\infty(t) - C(R,t)]$$

### 3. 移动收缩边界变换 (问题4)
对于半径随时间缩小的移动边界 $R(t)$，通过引入无量纲移动坐标 $\xi = r / R(t) \in [0, 1]$，将移动物理域转换为固定计算域，严格保留网格对流拟速度修正：

$$
\left.\frac{\partial C}{\partial t}\right|_\xi = \frac{\dot{R}(t)}{R(t)} \xi \frac{\partial C}{\partial \xi} + \frac{1}{R^2(t)} \frac{1}{\xi} \frac{\partial}{\partial \xi} \left( \xi D(C,T) \frac{\partial C}{\partial \xi} \right)
$$

离散方案采用有限体积法（FVM），严格保证非均匀收缩过程中的水分质量守恒。

---

## 各问题求解核心结论速查 (Key Results)

| 研究问题 | 物理假定 | 求解时间段 | 核心结论与物理现象 |
| :--- | :--- | :--- | :--- |
| **问题1** | 常物性、固定半径 ($R=2\text{cm}$) | $0 \sim 1800\ \text{s}$ (0.5 h) | 传热速率远快于传质。1800s时表面温度升至 $36.79^\circ\text{C}$，中心升至 $33.58^\circ\text{C}$；而水分仅在外层发生脱附（表面降至 $1.51\ \text{kg/kg}$，中心仍保持初始 $2.55\ \text{kg/kg}$）。 |
| **问题2** | 变物性、固定半径 ($R=2\text{cm}$) | $0 \sim 10800\ \text{s}$ (3.0 h) | 随温度升高及含水率下降，有效扩散系数 $D(C,T)$ 动态变化。3h时药材整体接近烘房温度 ($49.85^\circ\text{C} \sim 49.97^\circ\text{C}$)，中心水分降至 $1.766\ \text{kg/kg}$，表面水分降至 $1.008\ \text{kg/kg}$。 |
| **问题3** | 变物性、固定半径、阈值判定 | $0 \sim t_{\text{end}}$ (直至各处 $\le 0.15$) | **干燥终点时刻**：连续事件时刻为 **$57.47\ \text{h}$**（$206901\ \text{s}$）；按每分钟采样提交表格末时刻为 **$57.48\ \text{h}$**。终点由药材中心水分决定。 |
| **问题4** | 变物性、**动态收缩移动边界** | $0 \sim t_{\text{end}}$ (直至各处 $\le 0.15$) | **干燥终点时刻**：连续事件时刻为 **$51.09\ \text{h}$**（$183914\ \text{s}$）；表格末时刻为 **$51.10\ \text{h}$**。终点时药材半径收缩至 **$1.2000\ \text{cm}$**。**边界收缩使干燥时间缩短了 $6.38\ \text{h}$（加速 $11.11\%$）**，主因是扩散路径缩短了 $40\%$。 |

---

## 核心量化校验与稳健性指标 (Verification Metrics)

- **解析解对比误差**：在第一类与第三类边界常系数解析解对比中，$L_2$ 相对误差 $< 1.8 \times 10^{-4}$，确认求解器具备二阶空间收敛精度。
- **守恒律检验**：全时段总水分积分损失量与边界流出通量累计值相对偏差 $< 0.05\%$。
- **网格无关性 (GCI)**：空间网格从 $N=50$ 加密至 $N=200$，关键截面相对变异指数小于 $0.12\%$，数值解达到网格无关解。
- **边界扰动敏感度**：对烘房环境测量数据加入 $\pm 5\%$ 高斯白噪声，干燥完成时间波动在 $\pm 0.8\%$ 以内，模型具备高度鲁棒性。

---

## 复现运行指南 (Quickstart)

环境依赖：Python 3.10+，核心依赖包含 `numpy`, `scipy`, `pandas`, `openpyxl`, `matplotlib`。

```bash
# 1. 安装基础依赖
pip install numpy scipy pandas openpyxl matplotlib

# 2. 运行完整求解引擎（约需 2~3 分钟）
python solve_all.py

# 3. 导出正式提交表格至 results/
python export_results.py

# 4. 执行模型严谨性验证与数据校验
python validate_model.py
python verify_results.py

# 5. 生成论文全套可视化图表
python plot_results.py
```
