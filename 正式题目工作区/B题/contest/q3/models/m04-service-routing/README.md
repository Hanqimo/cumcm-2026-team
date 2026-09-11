# M04 / v5 第三问服务路径与沿途补测研究

本轮继续以200秒/点为目标，保留v3/v4作同场对照，比较多个结构性策略。最终候选v5采用六种覆盖布局朝向、测量进入/清除离开任务代价、收费的沿途补测；其他功能根据实验取舍，没有全部叠加。

冻结后100场同场v3 **238.11**、v4 **234.90**、v5 **234.23秒/点**，全部全清。v5相对v4平均节省0.6652秒/点，配对95%区间[-1.8046,3.1351]包含0，不能认定稳定更好；旧版保留，**200秒目标仍未达成**。本地独立运行目录为`D:\math modeling\正式题目工作区\B-simulator\p3-service-routing-research`，源码与冻结版本一致。

| 内容 | 入口 |
|---|---|
| 本轮结果与目标判定 | [最终报告](verification/report-v1/本轮优化与结果.md) |
| 所有试验，含失败组 | [trials.md](verification/report-v1/trials.md) |
| 数学表述、约束、停止条件与边界 | [formulations/v01.md](formulations/v01.md) |
| 参数冻结及数据划分 | [selection-v05.md](verification/selection-v05.md) |
| 最终100场原始结果和逐动作证据 | [R018](runs/R018-frozen-audit/) |
| 另一种空间误差的30场测试 | [R019](runs/R019-frozen-random-checker/) |
| 动作重算、独立覆盖证据、运行包一致性 | [审计](verification/replay-and-package-v1/result.json) |
| 连续覆盖几何核验 | [160组及4解析例](verification/continuous-cover-v1/result.json) |
| 联合覆盖路径MILP核验 | [20组穷举对照](verification/milp-checks-v1/result.json) |
| 程序预检查和失败原因 | [失败记录](verification/preflight-and-failures.md) |
| 可运行候选 | [src](src/) / [使用说明](src/使用说明.md) |

开发集10000起，选择验证11000起，冻结后独立审计12000–12099；R014–R016为36场专门压力布局，R019为14000起的30场随机布局与棋盘误差。不同批次不直接用均值比较。每次重要运行保留完整源码快照、参数、场景、清单；R018/R019还保存全部实际动作。

`verification/information-diagnostic-v1`给予起初真实坐标，只用于信息成本诊断；不是在线策略，也不是理论下界，不参与200秒目标判定。不要拿其中的理想化数字冒充可运行结果。

复现最终审计可在仓库根目录运行，输出目录必须尚未存在。约100场7–14分钟，具体取决于机器与负载。

```powershell
python contest/q3/models/m04-service-routing/verification/benchmark.py --output contest/q3/models/m04-service-routing/runs/R020-user-replay --config contest/q3/models/m04-service-routing/configs/frozen-v05.json --start 12000 --count 100 --variants v3,v4,v5 --keep-actions
```

这是已审计场景复跑，不是新留出集。历史开发版本以各自source_snapshot为准，当前代码不保证重现已经修复的失败实现。运行环境为Python3.10、NumPy2.2.6、SciPy1.15.3；绘图还用Matplotlib。新几何和MILP核验脚本默认创建独立结果目录，历史结果不得覆盖。

重新运行数学核验时，用`check_continuous_cover.py --output <新目录>`或`check_milp.py --output <新目录>`；原核验脚本和数学模块保存在各验证目录source_snapshot中。当前只补充了输出目录参数，数学检查逻辑不变。

本轮未连接官方模拟器，未更改团队adopted、全队STATUS或第四问。此前成果已在GitHub草稿PR #7，本轮M04新增内容保存本地，尚未提交推送。
