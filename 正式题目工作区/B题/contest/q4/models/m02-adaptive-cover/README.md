# 第四问22点覆盖候选

2026-09-11。新增独立研究候选 `polar22`。主留出40场原版696.78→新版515.63秒/点，均全清；平均改善26.00%，39场改善、1场退化。全部计入末尾排除与失败清除费用，未运行官方模拟器，未修改团队采用入口。第三问200秒/点目标仍未达到。

| 内容 | 入口 |
|---|---|
| 两问完整报告和退化分析 | [本轮报告](../../../paper/notes/q34-new-directions-v1/本轮优化报告.md) |
| 数学表述 | [v01](formulations/v01.md) |
| 全部试验，含未采用方案 | [trials](verification/trials.md) |
| 主结果数字 | [summary](verification/summary.json) |
| 冻结主试验 | [runs/R006-frozen-audit](runs/R006-frozen-audit/) |
| 运行包与散列 | [package](verification/package-v1.json) |
| 实际导出工厂复跑 | [replay](verification/package-replay-v1.json) |
| 源码与说明 | [src](src/使用说明.md) |

中心1点、980米内圈7点、1850米外圈14点，1334个凸子区域给出连续场地的方向排除条件。保留原v1定位和光学兜底。40场主审计配对95%区间[151.7753,210.5292]秒/点；最差种子26011增加145.79秒/点。48场压力/类型比例均全清且各组均值改善，不代表所有场景都更快。

开发24000–24011，选择25000–25011，冻结26000–26039；压力27000起，定向比例28000/28100起。主与压力88场新版共28497个动作、701684个子区域检查通过独立审核。选择12场的审核另存，不混入冻结主结果。几何布局可由verification/build_layouts.py重新构造，生成22/25点的坐标和子区域与发布文件完全一致。

运行包：`D:/math modeling/正式题目工作区/B-simulator/p4-adaptive-cover-research/run_practice.cmd`。

从仓库根目录复跑，输出目录必须不存在。策略本身本机单场一般低于1秒；日志和大型证书写盘另有耗时，40场通常数分钟。

```powershell
python contest/q4/models/m02-adaptive-cover/verification/benchmark.py --output contest/q4/models/m02-adaptive-cover/runs/user-replay --start 26000 --count 40 --policies directional_v1,polar22
```

独立复核将实际无信号点代入凸包半空间，检查每个子区域全部顶点及范围，不复用规划器的位集结论；场地与分区并集残差、逐动作时间差见verification/frozen-and-stress-audit-v1.json及type-profile-audit-v1.json。
