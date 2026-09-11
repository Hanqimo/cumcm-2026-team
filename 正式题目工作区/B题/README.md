# B题：第一至第四问最新研究成果

更新：2026-09-11。本目录集中保存四问模型、算法、运行结果、论文思路、失败尝试和可复现证据。**第三问200秒/点目标仍未达到；当前方案均为研究候选，新v6/polar22尚未官方演练。**

所有本次新增内容位于 `正式题目工作区/B题/`。旧根目录研究材料保留历史状态，本目录是这次四问成果汇总入口。

| 问题 | 最新思路与结果 | 直接入口 |
|---|---|---|
| 第一问 | 有界测向半平面交得到位置区域；最小包围圆判断能否保证清除；v02进一步求最近保证清除位置。v01有260项检查，补充投影有200例独立核验 | [模型与证明](contest/q1/models/m01-bounded-bearing/README.md)、[v02补充](contest/q1/models/m01-bounded-bearing/formulations/v02-clearance-projection.md) |
| 第二问 | 三圆盘交构造保证接收域，预算内选择第二观测点；v02利用当前区域与固定未知半径改进接收判据。有限搜索结果保留，不宣称连续全局最优 | [模型与推荐点](contest/q2/models/m01-reception-minimax/README.md)、[v02补充](contest/q2/models/m01-reception-minimax/formulations/v02-region-reception.md) |
| 第三问 | v6比较光学尝试与继续测向的后续耗时，保留非凸失败信息。60场冻结配对：v5 **234.03 → v6 232.60秒/点**，均全清，改善0.61%；极端/棋盘误差下优势消失 | [M05/v6](contest/q3/models/m05-action-value/README.md)、[完整数学表述](contest/q3/models/m05-action-value/formulations/v01.md) |
| 第四问 | 依据负观测凸包条件构造**中心1点＋980米内圈7点＋1850米外圈14点**；22点替代31点网格。40场冻结配对：**696.78 → 515.63秒/点**，改善26.0%，均全清 | [M02/22点](contest/q4/models/m02-adaptive-cover/README.md)、[覆盖推导](contest/q4/models/m02-adaptive-cover/formulations/v01.md) |

第四问39/40场改善，有1场明显退化；另48场压力及类型比例测试均全清，各组平均改善。第三问更新失败信息的单项效率贡献尚未证实。以上均为本地全场T/N结果，包含末尾排除与失败动作成本，不能替代官方正式测试。

## 阅读顺序

1. [四问思路与结果汇总](四问思路与结果汇总.md)。
2. [本轮第三、四问优化报告](contest/paper/notes/q34-new-directions-v1/本轮优化报告.md)，包含冻结比较、消融、压力与退化。
3. 各问的 `formulations/`、`src/`、`verification/`，以及第三问[全部试验](contest/q3/models/m05-action-value/verification/trials.md)、第四问[全部试验](contest/q4/models/m02-adaptive-cover/verification/trials.md)。
4. [本地与官方模拟器可替代性核查](contest/paper/notes/simulator-equivalence-audit-v1/本地与官方可替代性核查.md)。动作计费已对照官方演练日志，生成分布与固定误差场仍未知。
5. [历年相似子问题与优秀论文方法](参考思路/历年同类题研读/第三四问相似子问题与优秀论文处理方法.md)；已有[24篇论文索引与分析](../参考论文/B题/README.md)、[机制补充文献](../参考论文/B题/机制补充_2026-09-11/README.md)沿用仓库原位置。

## 目录与复现

本目录保留一个自包含的 `contest/` 子树，使四问之间的相对导入与证据链接可以复用。旧文档中“仓库根目录运行”的命令，在本归档中均应先进入 **`正式题目工作区/B题/`**。旧文档中的“本地未推送”等文字是当时记录，本次是否已上传以当前Git提交及本入口为准。

原始第四问结果包含重复的连续覆盖证书，单文件最大149 MiB，故q3/q4的完整`runs/`存为[无损ZIP归档](完整运行归档/)。网页保留每轮清单；第四问的`results-summary.json`只省略重复的`completion`字段，**不代替原始结果**。

```powershell
cd 正式题目工作区/B题
python restore_evidence.py --verify-only
python restore_evidence.py
```

恢复脚本校验全部SHA-256，按原路径还原，遇到不同内容的同名文件即停止，不覆盖本地改动。也可仅恢复一个模型：`python restore_evidence.py --model q4/m02-adaptive-cover`。全部恢复后约需0.8 GB磁盘空间。

安装各策略`src/requirements.txt`后，可以执行各模型README中的离线复现命令。最新可运行入口为[第三问run_robot.py](contest/q3/models/m05-action-value/src/run_robot.py)与[第四问run_robot.py](contest/q4/models/m02-adaptive-cover/src/run_robot.py)；使用者自行提供`--team`或本地`--config`。发布内容不包含团队连接配置、登录凭据、虚拟环境或Python缓存。

历史官方演练与最新本地实验分开保存；原始题面见[全局题面](contest/global/problem/B-v1/)。[归档清单](归档清单.json)记录来源文件、散列和归档位置。各问`adopted.md`仍保留未正式采用的状态，本次上传不代表团队采用或达标认定。
