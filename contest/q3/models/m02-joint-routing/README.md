# M02 第三问联合优化研究

**200 秒/点目标尚未达成。这里保存研究候选，不是已达标的最终方案。**

- 模型说明：[formulations/v01.md](formulations/v01.md)
- 当前冻结参数：[configs/frozen-candidates-v03b.json](configs/frozen-candidates-v03b.json)
- 结果报告：verification/research-report-v1/研究进展与结果.md
- 完整试验记录：runs/R001–R039，每个完整批次保存源代码快照、参数、逐场结果与哈希清单。
- 运行包入口：src/run_robot.py，可选择 route_guard、region_coupled、continuous_cover、combined_cover。
- 本地核验：verification/benchmark.py、integration_checks.py。

R025 存在数组比较程序错误，不能把失败时的短耗时当好成绩；R026 未形成完整清单；R035 输出截断后在 R039 按同一计划重跑。原始失败记录均保留。

批次重跑必须使用新的输出目录，例如：

```powershell
python contest/q3/models/m02-joint-routing/verification/benchmark.py --output contest/q3/models/m02-joint-routing/runs/REPRO-NEW --start 5100 --count 200 --config contest/q3/models/m02-joint-routing/configs/frozen-candidates-v03b.json --variants baseline,route_guard,region_coupled,continuous_cover,combined_cover
```

以上命令在 B题建模第一版仓库根目录执行，只调用独立本地物理世界，不连接官方模拟器。重现旧批次时以其 source_snapshot 为准，不能用当前文件冒充旧版本。

本模型使用第一、二问的候选几何结论，未改变团队 adopted，未执行提交或推送。
