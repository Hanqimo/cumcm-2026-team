# 问题一第一版模型

模型 Q1-M01-v01，算法 A01。推荐状态，尚未经团队正式采用。

- [完整数学表述与证明](formulations/v01.md)
- [可复用几何代码](src/bearing_geometry.py)
- [验证脚本](verification/verify_q1.py)
- 当前核验运行 [R003](runs/R003/manifest.json)，[260项检查](runs/R003/verification.json)
- [几何示意图](runs/R003/q1_geometry.png)，另存同名SVG
- [后续使用接口](../../common/v1-handoff.md)

最后一个接口入口由本目录外的 `contest/q1/common/v1-handoff.md` 统一记录，避免实验文件被误认为团队正式结果。

在仓库根目录执行 `python -X utf8 contest/q1/models/m01-bounded-bearing/verification/verify_q1.py --run-id R004` 可重新验证。运行编号必须未使用，以免覆盖历史证据。

依赖为 Python 3.10、NumPy、SciPy、Matplotlib。实际版本见运行清单。

R001在独立优化器检查中停止，未获得通过状态；R002修正独立验证的范数约束后通过；R003仅修正图片范围和注释并重新验证。当前程序没有调用模拟器。
