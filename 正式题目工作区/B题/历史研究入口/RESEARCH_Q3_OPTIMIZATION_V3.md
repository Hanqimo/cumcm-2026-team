# 第三问多策略优化进展

**当前最好冻结候选为 237.19 秒/点，尚未达到要求的 200 秒左右。**

最终 200 场同场景本地比较，旧版 317.38 秒/点；联合路径 240.41、区域收缩 238.71、连续覆盖 238.40、组合策略 237.19。全部场景全清、没有失败清除；组合策略另通过 60 场极端误差和布局压力验证。它们是合成世界结果，不是官方新成绩。

- [研究结果与不足](contest/q3/models/m02-joint-routing/verification/research-report-v1/研究进展与结果.md)
- [全部试验与失败记录](contest/q3/models/m02-joint-routing/verification/research-report-v1/trials.md)
- [数学模型与前两问衔接](contest/q3/models/m02-joint-routing/formulations/v01.md)
- [冻结参数](contest/q3/models/m02-joint-routing/configs/frozen-candidates-v03b.json)
- [运行说明](contest/q3/models/m02-joint-routing/src/使用说明.md)
- [上一次真实演练复盘](contest/q3/models/m01-region-routing/runs/R005-official-practice-analysis/演练复盘.md)

本地研究运行包位于相邻 B-simulator/p3-optimized-research，不覆盖 improved-p3 或已有演练记录。代码、参数、逐场结果、种子、失败记录、图表与模型说明均保留。

没有更改团队 adopted，没有提交或推送 Git。当前是未达到目标的研究进展，不能当成200秒方案交付完成。
