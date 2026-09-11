# B题机制补充文献：围绕现有瓶颈的8篇筛选

检索与核对日期：2026-09-11。研究基线：仓库 `298c8de`（本次开始时的 `origin/main`）。已核对题面、附件、Q1–Q4状态、Q3候选代码、失败记录及既有24篇全文和9条待获取线索。以下8篇均未在原清单中出现。

**优先读 B25、B26、B28：分别对应第四问定向盲区、第三问发现与路线联动，以及观测何时足够支持清除。** B27补充不依赖已知概率先验的交互覆盖框架；B30用于连续可行集与停止证明。B29、B31、B32分别补充路线的连续优化、有界估计和空间固定噪声。

- [结合现有成果的分析与逐篇迁移方案](分析与迁移建议.md)
- [7篇PDF全文](论文全文/)；B30已通过网页工具阅读作者公开全文，但本机下载连接失败，保留[作者全文入口](https://www.ensta-bretagne.fr/jaulin/paper_automatica93.pdf)。没有用其他论文替代或生成伪PDF。
- [8篇书目信息、版本与文件校验](文献清单.json)
- [BibTeX](references.bib)
- [检索与核验记录](检索与核验记录.md)

| 编号 | 论文简名 | 正式发表 | 本题用途 | 获取情况 |
|---|---|---|---|---|
| B25 | Achieving Full-View Coverage in Camera Sensor Networks | ACM TOSN, 2013 | Q4：未知朝向下的发现覆盖 | 作者公开期刊全文，31页 |
| B26 | Adaptive Submodular Ranking and Routing | Operations Research, 2020 | Q3：观测反馈与后续路线共同优化 | arXiv作者稿，28页 |
| B27 | Interactive Submodular Set Cover | ICML, 2010 | Q3/Q4：同时减少未知性并完成覆盖 | 会议全文，8页 |
| B28 | Near Optimal Bayesian Active Learning for Decision Making | AISTATS, 2014 | Q2/Q3：以可执行清除为观测目标 | 会议全文，9页 |
| B29 | A Branch-and-Bound Algorithm for the Close-Enough Traveling Salesman Problem | INFORMS J. Computing, 2016 | Q3：联合优化清除区域中的落点和顺序 | 作者预印稿，29页 |
| B30 | Set inversion via interval analysis for nonlinear bounded-error estimation | Automatica, 1993 | Q4：有界、非凸、带析取条件的可行集 | 已在线读全文12页；未下载 |
| B31 | 基于外定界椭球集员估计的纯方位目标跟踪 | 北京航空航天大学学报, 2017 | Q1/Q2：有界误差、外包与冗余观测 | 期刊全文，9页 |
| B32 | Optimal Decision Tree and Adaptive Submodular Ranking with Noisy Outcomes | JMLR, 2024 | Q2/Q3：同地重复测量不能平均消噪 | 期刊全文，42页 |

此目录是文献研究成果。迁移方案是针对B题提出的候选，不是原论文已经证明的B题算法；未新增模拟器测试、成绩或团队采用结论。期刊年份与下载稿件版本分别记录，避免把预印稿页码当成期刊页码。
