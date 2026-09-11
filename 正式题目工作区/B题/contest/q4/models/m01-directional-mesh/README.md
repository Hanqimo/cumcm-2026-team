# 第四问 M01：定向覆盖与可见性定位初版

当前为研究候选A01 v1.1，未登记团队采用。**第四问不能直接沿用第三问的负观测圆盘排除和全向搜索完成条件。** 初版采用31点等边三角网（18点在场外）覆盖未知朝向，结合有界定位、有限可见性假设评分、联合路线和光学区域后备。

冻结后40场混合随机场景：基线841.54、初版739.71秒/点，两版均全清；另24场压力场景均全清。初版依然偏慢，尚无官方演练成绩，不是200秒级最终方案。正文解释见[策略推导](formulations/v01.md)。

| 材料 | 入口 |
|---|---|
| 完整结果、退化与限制 | [初版及验证](verification/V003-final-audit/第四问初版与验证.md) |
| 数字唯一来源、配对数据 | [summary.json](verification/V003-final-audit/summary.json) |
| 连续几何与后备覆盖核验 | [V002](verification/V002-geometry/result.json) |
| 初次核验精度冲突与解决 | [V001](verification/V001-geometry/failure.json) |
| 最终40场完整动作/场景/源码 | [R006](runs/R006-final-v11/) |
| 最终边界朝外、切向、聚集压力 | [R007](runs/R007-final-outward/) / [R008](runs/R008-final-tangent/) / [R009](runs/R009-final-cluster/) |
| 运行代码与参数 | [src](src/) / [使用说明](src/使用说明.md) / [参数](src/policies.json) |
| 版本变更与失败记录 | [研究记录](verification/history.md) |
| 原题与前问来源 | [来源清单](verification/provenance.json) |

原始R001–R005保留第一次实现证据，不与最终版本混淆。新运行必须使用不存在的输出目录。仓库根目录复跑示例

```powershell
python contest/q4/models/m01-directional-mesh/verification/benchmark.py --output contest/q4/models/m01-directional-mesh/runs/R010-user-replay --start 25000 --count 40
python contest/q4/models/m01-directional-mesh/verification/check_geometry.py --output contest/q4/models/m01-directional-mesh/verification/V004-user-geometry
```

前者是已审计场景复跑，不是新留出集。Python3.10.11、NumPy2.2.6、SciPy1.15.3、Shapely2.1.2已测试；40场双策略约20秒，取决于机器和日志写入。运行快照含源码、参数与数据；Git HEAD只表示基准，当前有未提交文件，以各快照散列为准。

本地运行副本位于`D:\math modeling\正式题目工作区\B-simulator\p4-directional-research`，未连接官方接口。只更新第四问研究记录和成果导航，不改旧Q1–Q3源码或团队adopted、STATUS。新增成果本地保存，尚未提交推送。
