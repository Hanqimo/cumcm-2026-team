# 问题三改进演练策略入口

2026-09-11，本地实现，供用户演练；未提交、未推送。

运行：`D:\math modeling\正式题目工作区\B-simulator\improved-p3\run_practice.cmd`。

在模拟器选“问题3演练测试”，接口就绪后回程序按 Enter。自动复用旧策略队号和端口；不能同时运行两个策略。正式 API 未提供演练/正式模式查询。

本版保留测向历史、维护有界误差区域，选通过接收检查的侧向观测点，按当前位置就近清除，并用连续覆盖证书判断是否已完成全场搜索。

完整资料在 [模型入口](contest/q3/models/m01-region-routing/README.md)、[模型说明](contest/q3/models/m01-region-routing/formulations/v02.md)、[验证报告](contest/q3/models/m01-region-routing/verification/report.md)。

最终版通过 176 个离线合成场景和 4 项本地接口测试；独立 100 场留出集平均虚拟耗时下降 34.69%。这些不等于官方成绩；极近源聚集场景会劣于旧策略。官方效果等待用户运行。

运行后保留新包 `runs/时间戳/` 下的 summary、actions、源码快照，及模拟器结束界面、案例编码和官方 .jlog。后续先据真实演练复盘，不直接把本地百分比写为比赛效果。
