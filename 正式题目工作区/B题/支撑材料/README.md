# B题四问支撑材料

本目录归集第一、二问的完整数值求解代码，以及队友上传的第三、四问完整运行包、正式日志和复算资料。第三、四问来自团队上游提交 `656f33c`（代码包由 `0f1d872` 新增）；第一、二问来自本地 `第一二问完整数值求解_论文最新版`，逐文件来源与哈希见 `四问归集来源.json`。

## 目录与入口

| 内容 | 路径 | 入口 |
|---|---|---|
| 第一问：角域求交、顶点、区域直径及覆盖判断 | `q1-q2/q1/` | `q1-q2/run_q1.py` |
| 第二问：反馈预测、期望半径与完成概率加权选点 | `q1-q2/q2/` | `q1-q2/run_q2.py` |
| 一、二问输入、结果、验证和批量复算 | `q1-q2/examples/`、`reference_results/`、`verification/` | `q1-q2/reproduce_paper.py`、`verify.py` |
| 第三问全程协同（冻结标识 v6） | `q3/v6/` | `q3/v6/run_robot.py --policy v6` |
| 第四问联合域规划（冻结标识 M32） | `q4/M32/` | `q4/M32/run_robot.py --policy joint` |
| 三、四问对照策略、统计和绘图 | `q3/baselines/`、`q4/baselines/`、两问 `analysis/` | 见三四问原始说明 |
| 三、四问正式测试资料 | 两问 `formal/` | 共六份原始 `.jlog`、动作记录与结果 |

第一、二问保留为一个独立子包，以维持其编译、导入和批量复算路径。第三、四问的完整依赖模块及六份原始日志原样保留。

## 环境与快速检查

建议 Python 3.10 或以上。一、二问依赖 NumPy、SciPy；第二问还需要支持 C++17 的 `clang++` 或 `g++`。三、四问的依赖版本保留在根目录 `requirements.txt`。以下命令均在本目录执行。

```bash
python -m pip install -r requirements.txt
python -m pip install -r q1-q2/requirements.txt

# 文件完整性、Python语法及六份正式日志的记录核验，不联网
python verify_materials.py

# 第一问论文的数值计算示例及等边三角形反例
python q1-q2/run_q1.py q1-q2/examples/q1_orthogonal.json --out /tmp/q1_example.json
python q1-q2/run_q1.py q1-q2/examples/q1_triangle.json --out /tmp/q1_triangle.json

# 第二问从参数重新求解；输出目录应为新目录
python q1-q2/run_q2.py solve --a 0 --beta 0 --weights 0 0.5 1 --out /tmp/q2_origin

# 三、四问检查导入、策略和配置，不连接模拟器
python q3/v6/run_robot.py --policy v6 --team CHECK_ONLY --check
python q4/M32/run_robot.py --policy joint --team CHECK_ONLY --check
```

上述 `/tmp/` 输出路径适用于 macOS/Linux，可自行换成其他新路径。三、四问的实际运行需要题目模拟器和本队本地配置；具体步骤、基线参数和绘图命令见 [三四问原始说明](归集记录/三四问原始README.md)，其中相对路径均以当前支撑材料根目录为起点。第一、二问完整接口说明见 [一二问说明](q1-q2/README.md)。

## 与当前论文的对应关系

第一问正文已经精简为直径算法、直径圆覆盖判据、反例及数值示例。原代码中的最近清除位置模块和相关输出、检验作为历史扩展保留，不属于当前第一问正文的必答内容。复核本问时关注顶点、直径、最远点对和同直径圆覆盖结果。

第二问采用各分支剩余区域最小包围圆半径的期望 J，以及无需补测的完成概率 P_finish，加权目标为 `(1-w)*J/20 + w*(1-P_finish)`。本次只复制代码及已有数据，不改变算法、数值结果或三四问冻结策略。

`三四问支撑材料.zip` 是队友原始的三四问归档，不包含新增的一二问；四问完整材料以当前目录为准。队友提供的 `论文附录/` 和 `AI工具使用详情` 仍是三四问范围的原稿，本次未将它们扩写成全队版本。

`归集记录/三四问原始SHA256SUMS.json` 保留队友原始校验表，当前 `SHA256SUMS.json` 覆盖合并后的目录。来源、当前内容与原始版本可分别核对。
