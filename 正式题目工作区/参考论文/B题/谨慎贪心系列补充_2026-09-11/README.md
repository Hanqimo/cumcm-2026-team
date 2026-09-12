# 截图所指三篇论文：查重与补充

核对日期：2026-09-11；查重基线：`origin/main` 的 `4b094d2`。依据截图中的研究内容、会议/期刊年份核对原始书目，三篇对应如下。本轮只补缺少的ICRA 2012，不重复存放已收录的两篇。

| 截图线索 | 核实后的完整题名 | 作者 | 原库状态与全文 |
|---|---|---|---|
| ICRA 2012：主动选择观测位置的谨慎贪心 | Cautious greedy strategy for bearing-based active localization: Experiments and theoretical analysis | Joshua Vander Hook; Pratap Tokekar; Volkan Isler | 本轮新增B33：[6页PDF](论文全文/B33_ICRA2012_谨慎贪心主动定位.pdf) |
| ICRA 2013：有界不确定性下的传感器布设与选择 | Sensor Placement and Selection for Bearing Sensors with Bounded Uncertainty | Pratap Tokekar; Volkan Isler | 之前已收录，原库第1篇：[6页PDF](../论文全文/01_有界测角误差下的传感器布置与选择.pdf) |
| JFR 2014：理论完善与野外实验 | Cautious Greedy Strategy for Bearing-only Active Localization: Analysis and Field Experiments | Joshua Vander Hook; Pratap Tokekar; Volkan Isler | 之前已收录，原库第3篇：[23页PDF](../论文全文/03_兼顾移动与测量耗时的谨慎贪心主动定位.pdf) |

## 书目与来源

1. Vander Hook J, Tokekar P, Isler V. **Cautious greedy strategy for bearing-based active localization: Experiments and theoretical analysis**. 2012 IEEE International Conference on Robotics and Automation, 2012:1787–1792. DOI：[10.1109/ICRA.2012.6225244](https://doi.org/10.1109/ICRA.2012.6225244)。[明尼苏达大学书目](https://experts.umn.edu/en/publications/cautious-greedy-strategy-for-bearing-based-active-localization-ex/)；[作者公开会议稿](https://tokekar.com/pubs/vanderhook2012cautious.pdf)。
2. Tokekar P, Isler V. **Sensor Placement and Selection for Bearing Sensors with Bounded Uncertainty**. IEEE ICRA, 2013. DOI：[10.1109/ICRA.2013.6630920](https://doi.org/10.1109/ICRA.2013.6630920)。[作者页面](https://tokekar.com/tokekar2013asensor.html)；[作者全文](https://tokekar.com/pubs/tokekar2013asensor.pdf)。
3. Vander Hook J, Tokekar P, Isler V. **Cautious Greedy Strategy for Bearing-only Active Localization: Analysis and Field Experiments**. Journal of Field Robotics, 2014, 31(2):296–318. DOI：[10.1002/rob.21499](https://doi.org/10.1002/rob.21499)。[出版社页面](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.21499)；[作者页面](https://tokekar.com/vanderhook2014cautious.html)。

## 三篇的关系与B题用途

2012会议论文与2014期刊论文是同一研究线的早期成果和扩展成果。原库2014全文首页脚注明确说明，它整合两个2012年的早期工作，并增加理论结果和野外实验；参考文献中的2012b就是本次新增的ICRA论文。2013论文是同一团队围绕有界测角不确定性开展的相关研究，作者为Tokekar与Isler，不能把三篇的作者名单都写成相同。

- **2013**直接对应有界测角误差形成的扇形区域、传感器位置与选择，可用于B题前两问的几何模型。
- **2012**篇幅短，适合先理解主动选点、测量时间与移动时间的权衡，以及谨慎处理方位歧义的算法动机。原文采用高斯先验、测量噪声与EKF，主要看§II–IV；不能把其协方差保证直接替换成本题±1°固定误差下的20米安全清除保证。
- **2014**适合深入阅读完善后的分析、初始化与实验。有关移动和测量共同计费的借鉴，已在[原库逐篇分析](../B题论文逐篇分析与策略映射.md)第3篇说明。

截图中的“完整解决B题”属于原帖评价。三篇对定位核心有帮助，但本题未知源总数、多频道、确认没有遗漏和源的定向发射仍需单独处理；接收天线的180°方位歧义与发射源的半平面盲区也不是同一机制。

## 文件核验

本轮新增PDF来自作者网站，核验文件头、6页可解析性、首页题名与作者，并渲染检查首页。已存在的第1、第3篇均重新核对实际文件与旧清单SHA-256，一致。完整记录见[文献清单](文献清单.json)，新增引用见[BibTeX](references.bib)。本轮没有修改模型或运行模拟器。
