# 本地模拟器审计快照

标识：`b-official-calibrated-20260912`。本目录是团队唯一默认实现的原样提交快照，未创建另一套物理模型；仅用于审计论文中的本地对照，不能将结果称为官方成绩。

研究工作仍使用仓库 `contest/global/shared-src/local-simulator/run_local.py` 唯一入口。快照保留原始 defaults.json，其默认策略目录未重复打包；若独立核验快照，必须通过 `--strategy-dir` 显式指定本包策略，并设置匹配的 `--policy`，不能直接使用省略策略目录的默认命令。Q3 为 `--problem 3 --policy v6 --strategy-dir ../q3/v6`；Q4 为 `--problem 4 --policy joint --strategy-dir ../q4/M32`。工厂均为 `strategy:Planner`。完整参数用 `python run_local.py --help` 查看。

每场输出必须保留 manifest.json、模拟器/配置/策略哈希、fixtures、付费动作及全清率。重新生成默认场景不能代替论文固定 fixtures 的复核；已有逐场数据和代表性轨迹见 q3/analysis、q4/analysis。官方场景无法靠本地种子重建。
