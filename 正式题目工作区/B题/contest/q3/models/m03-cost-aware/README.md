# M03：前两问几何补充与第三问成本策略 v4

本轮候选已完成数学补充、开发对照、40场选择验证、24场压力测试和冻结参数后的100场独立审计。最后同场v3均值244.0157、新组合242.5808秒/点，平均降低0.5880%；配对节省近似95% t区间[0.1733,2.6964]秒/点。全部全清、无失败清除；65场改善、35场退化。200秒/点目标尚未达成，不能称官方成绩或团队正式采用。

| 内容 | 入口 |
|---|---|
| 数学结构、假设、代价与边界 | [formulations/v01.md](formulations/v01.md) |
| 原论文方法页、迁移范围和散列 | [阅读笔记](literature/reading-notes.md)、[来源](literature/provenance.json) |
| Q1/Q2新几何模块独立核验 | [结果](verification/q12-checks-v1/result.json) |
| 全部试验、统计、退化情况 | [结果报告](verification/report-v1/本轮改进与结果.md)、[试验表](verification/report-v1/trials.md) |
| 参数冻结决定 | [selection-v04.md](verification/selection-v04.md) |
| 最终源文件快照、场景和原始结果 | [R009](runs/R009-frozen-audit/) |
| 运行包与冻结代码一致性 | [integration-audit.json](verification/integration-audit.json) |
| 可运行源码、策略开关与日志 | [src](src/)、[使用说明](src/使用说明.md) |

Q1原型在 `contest/q1/models/m01-bounded-bearing/src/clearance_geometry.py`，Q2原型在 `contest/q2/models/m01-reception-minimax/src/reception_region.py`；本目录带相同字节的副本以便独立执行。两个v02数学补充也分别存放于前两问formulations。验证清单记录副本一致性，修改时须同步并重新验证，勿单独改其中一份后沿用旧结果。

新增局部策略包括最近保证清除点、利用现有区域的接收判据、按后续时间选下一测点、合并目标处扫描任务。失败方向包括中途追加多频道观测和只合并独立扫描站，均保存而未默认开启。整体是有安全证书的启发式，不是全局最优解。

在仓库根目录复现冻结候选时指定尚未使用的目录。约100场5–9分钟，机器和线程负载会影响耗时。

```powershell
python contest/q3/models/m03-cost-aware/verification/benchmark.py --output contest/q3/models/m03-cost-aware/runs/R010-user-replay --config contest/q3/models/m03-cost-aware/configs/frozen-v04.json --start 9000 --count 100 --variants baseline,combined
```

这是复跑已审计场景，不能称新留出集。另做推广测试需新种子并在测试前冻结参数。旧试验各自的源码快照为历史权威版本；直接用当前代码重跑旧开发配置不保证重现当时结果。

两个几何补充可独立复核：`python contest/q3/models/m03-cost-aware/verification/check_q12.py --output contest/q3/models/m03-cost-aware/verification/q12-user-replay`。输出目录同样必须未使用。原审计的脚本与两个几何模块保存于q12-checks-v1/source_snapshot；当前脚本只新增输出目录参数，核验逻辑相同。

新运行包仅做了离线自检与工厂一致性验证，未连接官方模拟器。旧v3目录完整保留。此前已有成果已上传GitHub草稿PR #7；本轮v4新增内容的保存级别为本地文件，尚未追加提交和推送。
