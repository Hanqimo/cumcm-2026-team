# 问题二第一版模型

模型 Q2-M01-v01，算法 A01。解析推导保证全向接收的候选区域，以移动预算约束下的最坏后验包围圆半径选择第二点。状态为推荐，非团队正式采用，非连续空间全局最优。

- [完整建模与候选区域证明](formulations/v01.md)
- [第二点与外包评价函数](src/second_point.py)
- [任意首次位置和方向的通用选点入口](src/planner.py)：`plan_next_observation(sensor, theta, budget)`；使用双侧较粗网格，与R002精细示例的网格不同
- [运行及验证脚本](src/run_q2.py)
- 当前运行 [R002清单](runs/R002/manifest.json)、[推荐点表](runs/R002/selected_points.csv)、[验证结果](runs/R002/verification.json)
- [候选区域和精度比较图](runs/R002/q2_candidate_and_tradeoff.png)
- [不同真实距离下的合成场景](runs/R002/q2_range_stress.png)
- [后续使用说明](../../common/v1-handoff.md)
- [通用入口边界场景检查V03](verification/V03/results.json)

从仓库根目录执行 `python -X utf8 contest/q2/models/m01-reception-minimax/src/run_q2.py --run-id R003`。运行编号必须未使用。依赖版本及源文件快照见运行目录。几何代码复用问题一的 `bearing_geometry.py`，运行快照保留其精确版本。

当前完整运行约17秒；不启动模拟器、不占用正式测试机会。R001保留了粗精度排序导致750米预算的入选点略逊于45°基线的发现，R002在最终分辨率下重新比较入围点和基线。

2026-09-11新增[后续几何补充](formulations/v02-region-reception.md)，作为第三问M03的候选接口；旧v01结果保留。
