# CUMCM 2026 Team Workspace

本仓库用于全国大学生数学建模竞赛的赛前准备和比赛期间协作。比赛期间可以在仓库中保存并共享题面、附件、数据、模型、代码、图表、计算结果和论文文件。

## 协作模式

全队按照题目顺序共同推进，一次集中研究一个小问。完成当前小问的理解、建模、求解和验证后，才整体进入下一问。仓库不为各小问设置固定负责人，也不使用编辑锁。

协作时遵循以下原则。

- `main` 只保存经过基本复核、能够继续依赖的稳定状态。
- 每个当前小问使用一个集体集成分支，例如 `stage/q1`。
- 具体模型、算法、数据检查、独立验证和写作使用短研究分支。
- 短研究分支通过 Pull Request 合并到当前小问的集成分支。
- 当前小问完成后，集成分支合并到 `main`，随后再从新的 `main` 开始下一问。
- Git 提交自动保留作者信息，因此状态文件不设置固定负责人字段。

## 仓库结构

```text
resources/                   赛前资料库
  problems/                  历年赛题、附件、索引和下载工具
  papers/                    优秀论文、讲评、索引和下载工具
  knowledge/                 建模方法、领域知识和复盘笔记
  datasets/                  训练用公开数据和样例数据

skills/                      可复用的数学建模 AI 工作流 Skill
src/                         跨赛题、跨小问复用的通用代码
tests/                       通用代码测试和一致性检查
templates/                   论文、模型卡、实验记录和状态模板
notebooks/                   只存放可跨赛题复用的示例 Notebook

contest/                     本届比赛实时工作区
  STATUS.md                  当前小问、研究阶段和集成状态
  global/                    全题共享的题面、数据、约定和正式结果
  q1/                        问题一研究材料
  q2/                        问题二研究材料
  q3/                        问题三研究材料
  q4/                        问题四研究材料
  paper/                     论文源码、图表、笔记和提交版本
```

目录的详细说明分别见 [赛前资料库](resources/README.md) 和 [比赛工作区](contest/README.md)。

## 文件归属原则

### 赛前资料

历年赛题、优秀论文、官方讲评、知识库和训练数据统一放在 `resources/`。同一份原始资料只保存一份，并通过索引记录年份、题型、主题、来源和本地路径。

### 全题共享内容

只有以下内容放入 `contest/global/`。

1. 当前题目的题面、官方附件和全题共同使用的原始数据。
2. 至少被两个小问共同使用的符号、假设、参数、代码或处理结果。
3. 已经核验并允许后续小问或论文引用的正式结果。

只服务于某一个小问的文件应留在该小问目录，不能因为“以后可能有用”而提前堆入 `global/`。

### 单个小问

每个小问以模型为基本研究单元。推荐结构如下。

```text
q1/
  state.md                   当前阶段、已确认结果和未决问题
  research-log.md            尝试过程，包括被否决的方案
  decisions.md               重要选择及其理由
  comparison.md              候选模型比较
  adopted.md                 当前正式采用方案的唯一入口
  common/                    该问多个模型共同使用的内容
  models/
    m01-baseline/
      README.md              模型说明和适用范围
      formulations/          数学表述的实质版本
      src/                   求解代码
      configs/               参数和算法配置
      notebooks/             探索性计算
      runs/                  可复现的运行结果
      verification/          独立验证和测试
  exports/                   提供给后续小问和论文的正式输出
```

`q1` 只是示例，其他小问采用相同规则。尚未开始的小问可以只保留入口说明，避免在前序结果未确定时过早建立模型。

### 论文

论文源文件统一放在 `contest/paper/`。正文按章节拆分，问题一至问题四分别使用独立的章节文件，降低多人同时修改同一文件产生冲突的概率。进入论文的数字、表格和图形必须能够追溯到对应小问的正式输出。

## 模型、算法和运行版本

使用以下标识区分不同层次的版本。

- `M01`、`M02` 表示不同模型或模型族。
- `v01`、`v02` 表示同一模型数学结构的实质变化。
- `A01`、`A02` 表示不同求解算法。
- `D01`、`D02` 表示不同数据版本。
- `R001`、`R002` 表示不同计算运行。
- `V01`、`V02` 表示不同验证方案。

普通文字修改、代码修复和参数微调由 Git 历史管理，不为每次修改复制一个新目录。只有变量、目标函数、约束、关键假设或数学机制发生变化时，才建立新的模型版本。

每次重要运行应在自己的运行目录中保存 `manifest.yaml`，至少记录模型、算法、数据、Git 提交、执行命令、随机种子和验证状态。已经被论文或后续小问引用的运行结果不得静默覆盖，新计算应建立新的运行编号。

## 逐问推进流程

### 1. 开始当前小问

先从最新的 `main` 建立集体集成分支。以下以问题一为例。

```bash
git status --short --branch
git switch main
git pull --ff-only
git switch -c stage/q1
git push -u origin stage/q1
```

随后更新 `contest/STATUS.md` 和 `contest/q1/state.md`。

### 2. 开展一项研究

模型、算法或验证工作从当前集成分支建立短分支。

```bash
git switch stage/q1
git pull --ff-only
git switch -c q1/model-m01
```

分支按照研究目的命名，不按照人员命名。推荐形式包括：

```text
q1/framing
q1/data-check
q1/model-m01
q1/model-m02
q1/solve-m01
q1/verify-m01
q1/writeup
```

完成一个可审查的小阶段后，显式暂存本次文件并检查差异。

```bash
git status --short
git add -- <本次文件路径>
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "add q1 baseline model"
git push -u origin q1/model-m01
```

随后创建以 `stage/q1` 为目标分支的 Pull Request。即使一个方案最终被否决，也应把结论和否决理由写入 `research-log.md` 或 `decisions.md`，避免全队重复走同一条无效路径。

### 3. 完成当前小问

只有理解、模型、算法、计算和独立验证达到当前约定的完成标准后，才能在 `adopted.md` 中确定正式方案，并把提供给后续小问的内容写入 `exports/`。

确认无误后，将 `stage/q1` 合并到 `main`，并在合并后的 `main` 上创建阶段标签。

```bash
git switch main
git pull --ff-only
git tag -a q1-complete -m "complete and verify question 1"
git push origin q1-complete
```

进入问题二时，从包含问题一正式结果的最新 `main` 创建 `stage/q2`。

如果后续发现前问需要修正，应建立 `fix/q1-...` 分支，并同时检查 `contest/global/dependencies.md` 中列出的后续影响，不能只修改前问数字而不重新核查后问。

## 三种保存级别

“保存文件”“Git 提交”和“团队共享”是三种不同操作。

- 本地保存只创建或修改文件，不提交、不推送。
- 检查点提交在审查后提交到当前短分支，但不推送。
- 团队共享在提交后推送当前短分支，并创建或更新 Pull Request。

用户或队员只说“写入文件”时，不应自动理解为允许提交或推送。只有明确要求“提交”时才创建提交，明确要求“推送、同步或共享”时才修改远程仓库。

## 并发修改规则

本仓库不使用编辑锁。多人同时研究同一问题时，采用以下方式降低冲突。

- 每项短期研究使用独立分支，并尽量修改独立文件。
- 不在同一个分支上进行未经协调的并发推送。
- 文本冲突逐段核对，不整文件采用一方版本覆盖另一方版本。
- Excel、Word、PDF 和图片等二进制文件无法可靠合并时，各分支创建不同版本文件，再由 Pull Request 明确选择或整合。
- 原始题面和原始数据只新增，不原地修改；清洗和转换结果由代码生成。
- 论文正文拆分为多个章节文件，`main.tex` 只负责整体结构和引用。

## 全局结果的发布

当前小问的实验结果首先留在模型运行目录。只有经过核验、准备被后续小问或论文引用的内容，才发布到 `contest/global/accepted-results/`。

发布时必须同时记录来源模型、运行编号、Git 提交、假设、误差范围和适用条件。后续小问不得从任意实验目录挑选数字，只能使用 `adopted.md`、`exports/` 或 `accepted-results/` 指向的正式结果。

## Git 安全规则

开始写文件前先检查仓库状态。

```bash
git rev-parse --show-toplevel
git status --short --branch
git diff --name-status
git ls-files --others --exclude-standard
```

工作开始前已经存在的修改和未跟踪文件视为其他重要工作，不得覆盖、撤销或夹带进本次提交。提交时只显式暂存本次文件，不使用 `git add .`、`git add -A` 或 `git commit -am`。

除非明确要求并已经确认影响，不执行 `git reset --hard`、`git clean -fd`、`git restore .`、`git rebase`、`git commit --amend` 或任何强制推送。

密钥、Cookie、账号信息、个人环境文件、缓存和 LaTeX 中间文件不得提交。赛题、数据、结果、图表和论文可以提交，但大型二进制文件在首次加入历史前应评估是否需要 Git LFS。

## 相关说明

- 详细协作规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 当前比赛工作区说明见 [contest/README.md](contest/README.md)。
- 历史资料和知识库说明见 [resources/README.md](resources/README.md)。
- 已有数学建模 Skills 见 [skills/](skills/)。
