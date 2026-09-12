# 无分布信息的最坏半径求解

主报告见[结果与对比](结果与对比.md)，机器可读结果见[comparison.json](runs/R001/comparison.json)，保守1%候选网格见[candidates_1pct_grid5.csv](runs/R001/candidates_1pct_grid5.csv)。本目录对应模型 `Q2-WC-U-v01`、运行 `R001`，基准为第一点原点、示向度正东。

北侧数值解约为 (969.35, 497.73) 米，最坏半径约49.03634米；南侧由反射得到。与原期望方案比较，最坏半径下降约2.66%，在相同均匀先验比较环境下的期望半径上升约1.57%。连续全域目标值的数值上下界相差小于0.001米，详见报告中的双精度运算限制。

复现命令为 `python3 src/reproduce.py`，需要 NumPy 和 clang++；本机可使用 `/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`。复现只更新本目录的运行与验证产物，不覆盖上级目录的基础模型结果。首次运行前应确认上级 `src/solver.cpp`、`src/search.py` 与 `src/verify_geometry.py` 匹配本目录清单中的来源哈希。

两种目标的期望比较采用原均匀联合先验并条件化于首次观测；最坏选点本身不采用这些概率假设。结果为本地研究候选，未自动正式采用、提交或推送。
