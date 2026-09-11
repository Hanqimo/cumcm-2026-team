# B题前两问第一版建模

前两问第一版已完成，保存了数学推导、可执行算法、合成实验、独立核验、图表、文献依据及后续接口。当前为研究分支推荐方案，尚非团队最终采用。本轮从GitHub最新main取得资料，成果仅保存本地，未提交或推送。

## 从这里阅读

1. [问题一完整建模](contest/q1/models/m01-bounded-bearing/formulations/v01.md)：正向角域、半平面交、顶点直径、同直径圆判定、可实现反例和20米清除条件。
2. [问题二完整建模](contest/q2/models/m01-reception-minimax/formulations/v01.md)：保持接收的三圆盘候选区域、非退化筛选、最坏后验半径目标、预算策略族和保守数值方法。
3. [自动生成的数值比较表](contest/paper/tables/q12-v1-results.md)：原点首次测得0°时的四种预算示例，不是模拟器成绩。
4. [文献依据与自主推导界限](contest/paper/notes/q12-v1-literature.md)、[BibTeX](contest/paper/bibliography/q12-v1.bib)、[写作交接](contest/paper/notes/q12-v1-writing-handoff.md)。
5. [问题一后续接口](contest/q1/common/v1-handoff.md)、[问题二后续接口](contest/q2/common/v1-handoff.md)。

## 关键结果

问题一的定位区域直径等于最远顶点对距离，但一般不存在同直径覆盖圆。边长38米的等边三角形可由本题三个测向角域形成，其最小包围圆半径约21.939米。因此D≤40不能作为保证清除条件；正确条件为最小包围圆半径R≤20。

问题二先利用首次已接收所包含的“有效半径不小于首次真实距离”约束，推导只依赖首次位置和方向的保证接收候选域，再在移动预算内比较最坏后验包围圆。数值推荐仅对有限候选搜索成立，没有连续全局最优或全题最短总时间的证明。

在当前原点示例中，1000米移动预算的推荐点仍有约56米的最坏后验半径上界，并存在超过20米的实际合成后验，故这套一步策略不能普遍保证两次观测就可清除。靠近圆域边界时，目标先验可能显著收缩，必须重算。

## 验证与复现

- 问题一当前运行 [R003](contest/q1/models/m01-bounded-bearing/runs/R003/manifest.json)，260项检查，独立LP支持函数与凸范数优化核验。
- 问题二当前运行 [R002](contest/q2/models/m01-reception-minimax/runs/R002/manifest.json)，1305项检查，包含1100条合成方向工况。
- 问题二另有 [V02独立表示核验](contest/q2/models/m01-reception-minimax/verification/V02/result.json)，40例后验区域采用另一构造及LP支持函数对照。
- [通用选点入口](contest/q2/models/m01-reception-minimax/src/planner.py)支持任意首次位置和方向，并通过V03原点、边界、非轴向和预算过小四种情况的集成检查；它与R002精细示例使用不同空间网格。
- 原始输入与七篇核心文献PDF的[来源和SHA-256](contest/paper/notes/q12-v1-provenance.json)已留存。运行目录保存精确源码快照、环境版本、命令、种子、原始数值和PNG/SVG。

从本目录运行下列命令。每次使用新的运行编号，已有结果不会被静默覆盖。

```powershell
python -X utf8 contest/q1/models/m01-bounded-bearing/verification/verify_q1.py --run-id R004
python -X utf8 contest/q2/models/m01-reception-minimax/src/run_q2.py --run-id R003
```

表格及文献索引生成命令为 `python -X utf8 contest/paper/notes/build_q12_v1_record.py`。脚本读取当前选定Q1-R003/Q2-R002，不会自动把新运行升级为采用版本。独立验证脚本默认V02目录不可覆盖，复验时应另取编号。

当前数学运行环境为Python 3.10、NumPy 2.2.6、SciPy 1.15.3、Matplotlib 3.10.8，具体版本以运行清单为准。没有运行模拟器，也没有编写问题3、4完整策略。

## 尚需保留的边界

±1°是否已经包含接口四舍五入仍需核对；本版有1.005°保守敏感性。问题一浮点求交不是任意病态输入的严格区间算术证书。问题二的三圆盘区域是通用充分区域，可能因忽略圆域裁剪和near机会而保守；其全向接收保证不能移植到第四问。

全队`STATUS.md`及各问`adopted.md`未被改写成已采用状态。下一步适合由队员审阅这两版的假设、目标与证明，再决定哪些内容进入正式模型及后续调度。
