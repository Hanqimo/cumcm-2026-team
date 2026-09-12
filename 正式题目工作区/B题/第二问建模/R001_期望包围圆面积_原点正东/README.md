# 原点、正东基准的第二检测点求解

本目录是一个独立结果包。原模型保存在上一级，本次采用的版本快照为 `model_snapshot.tex`，其 SHA-256 在 `config.json` 中。所有数值均为本地自主计算，没有调用竞赛模拟器。

**主结论：**在源位置面积均匀、角误差在 ±1° 内均匀且不同地点条件独立、同一源接收半径先验为 Uniform(1000,1500) 的假设下，数值最优第二点约为 \((932.6,\pm590.0)\) 米，最小包围圆的期望面积约为 **2103.7834 平方米**。详细说明见 `求解报告.pdf`，可编辑稿为 `求解报告.tex`。

若要求第二次对后验允许的所有环境都保证接收，则北侧数值最优点约为 \((864.316,511.356)\) 米，南侧镜像等价，期望面积为 **2228.8321 平方米**，较主模型高约 **5.94%**。主模型无信号概率约为 **0.06726%**；包围圆半径不超过 20 米的概率分别为 **20.6622%** 和 **34.1389%**。该概率表示移动至反馈后的包围圆圆心可获得统一的 20 米保证，不是第二检测点立即清除的概率。

本结果是有界全域网格与局部细化得到、经多种数值检查的数值最优结果，**没有连续全局最优证明**。移动耗时仅作为辅助指标，未加入期望面积目标。

## 文件索引

| 文件 | 用途 |
|---|---|
| `求解报告.pdf` / `求解报告.tex` | 结论、模型计算口径、候选图、核验和敏感性 |
| `config.json` / `model_snapshot.tex` | 输入与模型版本 |
| `src/solver.cpp` | C++17 概率积分、连续几何包围圆和搜索点评价 |
| `src/reproduce.py` | 主要结果或全网格复现入口 |
| `src/verify_geometry.py` | NumPy 射线区间独立几何核验 |
| `src/summarize.py` | 汇总与必要断言检查 |
| `results/summary.json` | **最终权威汇总**；机器可读 |
| `results/comparison.csv` | 精度级别 5 的主方案、镜像、安全方案和基线比较 |
| `results/candidates_1pct.csv` / `candidates_5pct.csv` | 北侧 1% / 5% 损失容差的 5 米网格候选点 |
| `results/*_input.csv` | 各阶段完整输入网格，保留以精确复现 |
| `verification/checks.json` | 数值验证摘要 |
| `verification/convergence.csv` | 同点多精度收敛记录 |
| `verification/independent_geometry.json` | 47 个射线几何核验案例 |
| `verification/mc_main_final.json` / `mc_safe.json` | 50 万次后验模拟及种子 |
| `figures/candidate_region.tex` | PGFPlots 科研候选区域图 |
| `manifest.json` | 数据、源码、文档散列及运行环境 |

其他 coarse/refine/prior 文件均为中间搜索结果。粗精度的 `P20` 只用于粗筛，最终报告使用高精度阈值切分结果。`best_grid.json` 保留 0.5 米搜索阶段的历史结果；最终坐标与指标以 `summary.json` 和 `comparison.csv` 为准。候选集的坐标投影不是整个矩形都可接受；南侧候选点取镜像，连续点用 `eval` 复算。

## 快速复算

核心求解器仅需 C++17 编译器，无第三方数值库。在本目录执行以下命令。

```sh
clang++ -std=c++17 -O3 src/solver.cpp -o solver
./solver eval 932.6 590 5
./solver eval 864.316399410232 511.3558109716 5
./solver mc 932.6 590 500000 912732
```

`eval x y level [prior]` 的距离单位为米，返回 J 的单位为平方米，概率为 0 至 1；`level` 为 0 至 5，最终评价建议 5。`prior=0` 表示半径均匀，`prior=-1` 表示半径密度线性下降，`prior=1` 表示线性上升，后两者的支持仍为 [1000,1500]。`mc` 当前仅实现均匀半径先验，不可用它验证其他先验。

`batch input.csv output.csv level [prior]` 逐个计算指定点。`geometry x y kind theta` 输出支持集的圆弧及包围圆上下界，其中 kind 为 0（强信号）、1（正常）、2（无信号），theta 单位为弧度。`profile` 输出正常反馈的密度与圆半径。

## 一键复现

Python 需安装 NumPy，用于结构独立的射线几何核验；其余 Python 步骤只需标准库。当前机器已验证可用的解释器为下面这个捆绑运行时，其他带 NumPy 的 Python 3.9+ 也可使用。

```sh
/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/reproduce.py
/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/reproduce.py --full
```

第一条复算主要结果和独立检查；第二条额外重算全部已保存网格，运行时间更长。脚本会重写本结果包内对应的派生结果文件，不修改上一级模型文件。完整搜索用了 100/50 米全域网格以及 10/2/0.5/0.1 米局部网格，半径先验敏感性另作 50/5/1 米搜索。临界候选点使用精度 5 复核，其余候选点使用精度 3。

编译报告使用 XeLaTeX 和 PGFPlots，Fandol 字体由 TeX Live 提供。

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build 求解报告.tex
cp build/求解报告.pdf 求解报告.pdf
```

## 精度与限制

主最优点在精度级别 4 和 5 之间的面积变化为约 0.00000281 平方米；最终概率归一化残差约为 9.06e-13。几何核验使用 12001 条独立极坐标射线，46 个非空案例的包围圆上界与射线点直径下界最大差约为 0.002341 米，全部射线点覆盖残差小于 1e-5 米。蒙特卡洛与积分均值在三个标准误以内，抽样源均被覆盖。

这些检查验证本次实现和指定输入，不证明假设符合未知真实环境，也不证明连续全局最优。最小基线 1 米只是计算排重设置，不能解释为误差独立的物理相关长度。原点以外的第一点必须重新裁切目标圆域，本求解器当前专用于原点、正东基准，不能直接平移套用。
