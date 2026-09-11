# 第三问光学动作价值候选

2026-09-11。新增独立研究候选 `v6`。主留出60场原版234.03→新版232.60秒/点，均全清；平均改善0.61%，54场改善、6场退化。全部计入末尾排除与失败清除费用，未运行官方模拟器，未修改团队采用入口。第三问200秒/点目标仍未达到。

| 内容 | 入口 |
|---|---|
| 两问完整报告和退化分析 | [本轮报告](../../../paper/notes/q34-new-directions-v1/本轮优化报告.md) |
| 数学表述 | [v01](formulations/v01.md) |
| 全部试验，含未采用方案 | [trials](verification/trials.md) |
| 主结果数字 | [summary](verification/summary.json) |
| 冻结主试验 | [runs/R004-frozen-audit](runs/R004-frozen-audit/) |
| 运行包与散列 | [package](verification/package-v1.json) |
| 实际导出工厂复跑 | [replay](verification/package-replay-v1.json) |
| 源码与说明 | [src](src/使用说明.md) |

v6只在当前可行区域半径不超过100米时比较光学试探和无线电继续定位，保留失败排除产生的非凸区域。60场主审计的配对95%区间为[1.0976,1.7591]秒/点；固定极端/棋盘误差下优势消失，不能称普遍提速。单独更新失败信息的20场消融差异不稳定。旧v5保持原样，新沿途价值补测及融合不采用。

开发15000–15011，选择16000–16019，冻结17000–17059；消融18000–18019，压力19000/19100/19200起。独立几何、持久排除、物理动作和覆盖核验见verification内JSON。源快照保留每轮实际版本；导出策略工厂经2场离线复跑与主审计逐项匹配。

运行包：`D:/math modeling/正式题目工作区/B-simulator/p3-action-value-research/run_practice.cmd`。

从仓库根目录复跑，输出目录必须不存在。60场双策略按本机历史每场数秒到约15秒，通常数分钟至十余分钟，受负载影响。

```powershell
python contest/q3/models/m05-action-value/verification/benchmark.py --output contest/q3/models/m05-action-value/runs/user-replay --config contest/q3/models/m05-action-value/configs/frozen-v06.json --start 17000 --count 60 --variants v5,v6 --keep-actions
```
