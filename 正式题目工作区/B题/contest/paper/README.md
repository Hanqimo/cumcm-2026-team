# 论文工作区

本目录保存本届比赛论文的 LaTeX 源文件、章节草稿、采用的图表和表格、写作笔记以及提交版本。全队共同参与论文审阅，不设置固定章节负责人，也不使用编辑锁。

## 推荐结构

```text
main.tex
sections/
  abstract.tex
  problem.tex
  assumptions.tex
  q1.tex
  q2.tex
  q3.tex
  q4.tex
  analysis.tex
  conclusion.tex
figures/
tables/
bibliography/
notes/
build/
submission/
```

正文按章节拆分，研究分支尽量修改独立章节。`main.tex` 只负责整体结构、宏定义和文件引用。发生文本冲突时逐段核对，不整文件覆盖。

论文中的数字、表格和图形只能来自各小问的 `adopted.md`、`exports/` 或 `global/accepted-results/`。图表进入论文目录时，应记录来源小问、模型版本、运行编号和对应提交。

`build/` 只保存编译中间文件并被 Git 忽略。准备正式提交时，将经过检查的 PDF 保存到 `submission/`，使用 `paper-v01.pdf`、`paper-v02.pdf` 和 `final.pdf` 等明确名称。
