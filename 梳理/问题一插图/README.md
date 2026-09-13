# 问题一插图重绘记录

## 当前论文采用的版本（2026-09-13）

当前论文将等边三角形反例图放在“定位区域的覆盖”一节，引用 `q1-counterexample.pdf`。该图只显示边长 38 m 的三角形和半径 19 m 的直径圆，标出圆外顶点及 60° 夹角，不再与计算示例拼图。源代码为 `plot_q1_counterexample.py`，以解析坐标生成图形，等比例绘制，输出 110 × 70 mm 的矢量 PDF 和 400 dpi PNG；几何数值、字体及源文件散列见 `q1-counterexample-manifest.json`。

复现命令为 `python3 梳理/问题一插图/plot_q1_counterexample.py`，依赖 numpy、matplotlib；可用环境变量 `CJK_FONT` 指定中文字体。图内无总标题，总图名由论文 LaTeX 图注提供。

5.7.1 改为“数值计算示例”，正文直接列出输入、半平面约束、四个顶点、直径及覆盖判定，并单独引用 `q1-numerical-example.pdf` 展示角域边界、四个顶点、最远点对及包围圆。对应源码为 `plot_q1_numerical_example.py`，读取 R003 的全精度计算结果，输出 110 × 85 mm 的 PDF 和 400 dpi PNG。图中是原点附近的局部范围，两个距离原点1000米的检测点未在视窗内显示。复现命令为 `python3 梳理/问题一插图/plot_q1_numerical_example.py`；几何检查、源数据散列及字体记录见 `q1-numerical-example-manifest.json`。原 `q1-geometry.pdf/png` 及绘图代码保留为历史素材。图1 `q1-intersection-process.pdf` 继续使用。

## 以下为此前组合图的重绘记录

本目录保存论文图1、图2的可复现绘图代码及 PDF、PNG 输出。论文模版和初稿引用此处的矢量 PDF，旧 PNG 保留在上一级目录。

## 来源与几何含义

图1原图为 `梳理/q1-intersection-process.png`，由 SEREIN-na 在提交 `bd20f3e` 中加入。该提交未附绘图代码，当前仓库也未找到对应脚本，因此依据原图和论文的半平面交模型重新构造。示意图适当放大开角，不作为 ±1° 的数值算例。中间的四边形由两个前向角域实际求交得到；右图保留相同方向角域的无界交集，用两条带箭头的射线表示延伸，不用人为封口线表示有限区域。

图2原绘图代码位于 `contest/q1/models/m01-bounded-bearing/verification/verify_q1.py` 的绘图段，历史运行快照见 `contest/q1/models/m01-bounded-bearing/runs/R003/source_snapshot/verify_q1.py`。本次直接读取 R003 的 `counterexample.json` 和 `orthogonal_example.json`，不重新优化或更改顶点、圆心、半径。左图半径为 21.9393102292 m、直径圆半径为 19 m；右图两种圆重合，半径为 24.6927129119 m。

## 样式与排版

- 图1尺寸为 160 × 59 mm，检测点为圆点，角域为浅米色、交集为浅蓝色，取消红色及五角星。
- 图2尺寸为 135 × 78 mm，采用中文分图名和图例，坐标单位为 m，字号按论文最终尺寸设置。共享图例位于两幅子图下方。
- 总图名保留在 LaTeX 图注中；图内仅保留简短分图名、符号及必要说明。
- 原始图片、历史数值数据和验证脚本均保留。本次只调整两份主 TeX 中的图片路径及宽度。

复现命令为 `python3 梳理/问题一插图/plot_q1_figures.py`，依赖 numpy、matplotlib；中文字体默认使用本机 SimHei。环境、尺寸和数据哈希见 `manifest.json`。

绘图采用仓库内 `scientific-visualization` 技能的最终物理尺寸、字体嵌入、源数据保留及导出后检查流程，技能文件见 `正式题目工作区/B题/第二问建模/论文定稿版/论文插图_20260913/skill/SKILL.md`。
