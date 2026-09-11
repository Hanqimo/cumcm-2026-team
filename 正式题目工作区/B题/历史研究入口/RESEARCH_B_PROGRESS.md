# B题第一至第三问研究成果导航

本次按用户要求同步已有研究成果，包含前两问第一版建模、第三问两个模型族、真实演练复盘和多轮本地模拟。研究分支为 `codex/b-q1-q3-research-sync`。当前仓库没有远程 `stage/q1`–`stage/q3` 分支，因此通过面向 `main` 的草稿 PR 提供统一审阅入口，不自动登记 adopted 或合并为正式方案。

## 对应目录

| 内容 | 入口 |
|---|---|
| 题面和附件版本 | [B-v1](contest/global/problem/B-v1/) |
| 第一问：有界测角区域与清除条件 | [第一问状态](contest/q1/state.md) / [模型](contest/q1/models/m01-bounded-bearing/) |
| 第二问：保证接收与下一测点 | [第二问状态](contest/q2/state.md) / [模型](contest/q2/models/m01-reception-minimax/) |
| 前两问完整导读 | [第一版建模](RESEARCH_Q12_V1.md) |
| 第三问：原改进策略与实测复盘 | [M01](contest/q3/models/m01-region-routing/) / [真实演练复盘](contest/q3/models/m01-region-routing/runs/R005-official-practice-analysis/演练复盘.md) |
| 第三问：多策略联合优化 | [研究导读](RESEARCH_Q3_OPTIMIZATION_V3.md) / [M02](contest/q3/models/m02-joint-routing/) |
| 第三问完整比较与失败记录 | [结果报告](contest/q3/models/m02-joint-routing/verification/research-report-v1/研究进展与结果.md) / [全部试验](contest/q3/models/m02-joint-routing/verification/research-report-v1/trials.md) |
| 第三问可运行候选 | [源代码与启动脚本](contest/q3/models/m02-joint-routing/src/) / [使用说明](contest/q3/models/m02-joint-routing/src/使用说明.md) |
| 论文依据与交接 | [前两问交接](contest/paper/notes/q12-v1-writing-handoff.md) / [第三问交接](contest/paper/notes/q3-v3-writing-handoff.md) |

## 当前结论

最新[本地与官方可替代性核查](contest/paper/notes/simulator-equivalence-audit-v1/本地与官方可替代性核查.md)已读取8局用户实际官方演练记录。计费与1336个动作响应吻合，但本地随机生成分布未获官方确认，不能替代正式测试。新读取的Q3 v5两局为14/14、210.34秒/点和10/10、296.73秒/点；Q4一局15/15、687.81秒/点，其中14定向、1全向，提示本地普通50%定向假设需扩充。以下报告中的“暂无官方演练”描述保留其生成时的历史状态，以本次核查及各问state的最新补充为准。

第四问初版现已独立实现，见 [M01定向覆盖与定位](contest/q4/models/m01-directional-mesh/README.md)。31点三角网提供未知朝向的发现证书，结合可见性选点、联合路线与光学区域后备。40场同场全清：简单基线841.54、初版739.71秒/点；另24场压力全清，尚无官方演练。完整[分析与推导](contest/q4/models/m01-directional-mesh/formulations/v01.md)、[结果报告](contest/q4/models/m01-directional-mesh/verification/V003-final-audit/第四问初版与验证.md)和[运行说明](contest/q4/models/m01-directional-mesh/src/使用说明.md)已保存本地，未推送，不是200秒级最终方案。

2026-09-11继续优化第三问的新增成果见 [M04 v5](contest/q3/models/m04-service-routing/README.md)。本轮比较服务路径、覆盖朝向、沿途补测及前瞻、MILP等方向，冻结后100场同场结果为v3 **238.11**、v4 **234.90**、v5 **234.23秒/点**，全部全清。v5相对v4只减少0.6652秒/点，配对95%区间[-1.8046,3.1351]，不能认定稳定更好；保留v4，v5作为独立研究候选。**200秒目标仍未达成**。[完整报告](contest/q3/models/m04-service-routing/verification/report-v1/本轮优化与结果.md)、[运行说明](contest/q3/models/m04-service-routing/src/使用说明.md)及[写作交接](contest/paper/notes/q3-v5-writing-handoff.md)已保存本地，尚未追加提交推送。

2026-09-11上传后的新增研究见 [M03 v4](contest/q3/models/m03-cost-aware/README.md)：前两问新增最近保证清除点与区域接收判据；第三问新增完成时间选点和扫描任务合并。冻结后100场同场对比244.02→242.58秒/点，均全清，平均改善0.59%；200秒目标仍未达成。[本轮报告](contest/q3/models/m03-cost-aware/verification/report-v1/本轮改进与结果.md)和[写作交接](contest/paper/notes/q123-v4-writing-handoff.md)已保存本地，尚未追加提交推送。此前已有成果的GitHub审阅入口为[草稿PR #7](https://github.com/StevenKaiyi/cumcm-2026-team/pull/7)。

第三问M02历史200场配对本地模拟：M01旧版317.38秒/点，组合策略237.19秒/点；全部全清、没有失败清除。另有60场组合策略压力验证全部全清。**200秒/点目标尚未达成**，这些结果不能写成官方比赛成绩或最终达标方案。

## 克隆后的运行与复现

前两问和第三问的复现命令见各模型 README。每次重跑使用新的输出目录，不能覆盖已有研究证据。

第三问运行脚本可在其 src 目录直接执行，自检时使用自己的配置：

```powershell
python run_robot.py --check --config "本机配置文件路径"
python run_robot.py --policy combined_cover --config "本机配置文件路径"
```

配置含 `team_no` 和 `port`，个人配置没有随本次上传。历史代码快照中名为 `config.json` 的文件是本地试验参数，不是队号配置。软件安装、虚拟环境、Python缓存和外部本地运行目录未纳入 Git。

原始运行清单、图表来源和历史研究记录里的“未提交/未推送”描述保留计算当时的状态。文件中的 Windows 绝对路径用于来源追溯；其他机器应使用上表对应的仓库路径。此次同步不改写原始数值、失败记录或源码快照，实际同步版本由本分支 Git 提交记录标识。
