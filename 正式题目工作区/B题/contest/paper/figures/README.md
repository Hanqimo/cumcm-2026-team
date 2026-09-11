# 论文图形

只保存已经确认用于论文的图形。每张图应能够追溯到生成代码、模型版本、运行编号和 Git 提交，不在图像文件中手工修改数值结论。

## 本目录文件的来源记录

以下图件由各小问运行目录中的原始 PNG 复制而来（或从无损归档中提取），**内容未作修改**；数值结论以对应运行目录为准，图中标注为绘制时的取值。

| 文件名 | 论文中的图号 | 来源模型 | 运行编号 | 原路径 |
|---|---|---|---|---|
| `q1-geometry.png` / `.svg` | 图 1 | Q1 M01 有界测向 | R003 | `contest/q1/models/m01-bounded-bearing/runs/R003/q1_geometry.png` |
| `q2-candidate-tradeoff.png` | 图 2 | Q2 M01 接收 minimax | R002 | `contest/q2/models/m01-reception-minimax/runs/R002/q2_candidate_and_tradeoff.png` |
| `q2-range-stress.png` | 图 3 | Q2 M01 接收 minimax | R002 | `contest/q2/models/m01-reception-minimax/runs/R002/q2_range_stress.png` |
| `q3-joint-paired.png` | 图 4 | Q3 M02 联合路径 | R039 最终审计 / `verification/research-report-v1` | `contest/q3/models/m02-joint-routing/verification/research-report-v1/paired-comparison.png` |
| `q3-official-route.png` | 图 5 | Q3 M01 区域定位与就近清除 | R005 官方演练分析 | `contest/q3/models/m01-region-routing/runs/R005-official-practice-analysis/route-and-progress.png`（从 `完整运行归档/q3-m01-region-routing.zip` 提取） |

说明：

- 图 5 为真实官方演练（案例 JCEK-BMVS-WD8Z-WF6J）的轨迹与清除进度。图中绿色标记是**清除动作发生位置**，不是干扰源真实坐标。
- 第四问目前**没有**可用图件：22 点布局与 1334 个凸子区域的几何示意可由 `contest/q4/models/m02-adaptive-cover/verification/build_layouts.py` 重新构造，但尚未生成论文用图。该处留待补充。
- 图形当前使用英文轴标签并提供 SVG 便于最终统一字体。定稿前需要核对论文最终尺寸与字体嵌入，并按统一风格重绘。
