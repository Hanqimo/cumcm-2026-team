"""问题四混合全向/定向源M16后验规划策略；尚无官方实测。"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', choices=['joint'], default='joint', help='默认第四问M16后验规划策略')
    parser.add_argument('--team', help='默认复用旧策略的 config.json 队号')
    parser.add_argument('--port', type=int, help='默认复用旧配置，缺省端口 2026')
    parser.add_argument('--config', type=Path, help='指定含 team_no、port 的配置文件')
    parser.add_argument('--check', action='store_true', help='仅检查依赖和配置，不连接模拟器')
    args = parser.parse_args()
    try:
        import numpy
        import scipy
        import shapely
        from api_client import Robot, BudgetReached
        from strategy import Planner, VERSION, POLICIES
    except ImportError as error:
        print(f'缺少依赖：{error}\n请安装 requirements.txt 中的依赖后重试。')
        return 2
    paths = [args.config] if args.config else [ROOT / 'config.json', ROOT / 'config.json']
    config_path = next((p for p in paths if p and p.is_file()), None)
    config = json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path else {}
    team, port = args.team or config.get('team_no'), args.port or config.get('port', 2026)
    if not team:
        print('找不到队号配置，请使用 --config 指定旧 config.json，或使用 --team 参数。')
        return 2
    if args.check:
        print(f'策略 {args.policy}；第四问覆盖改进版，仅完成本地验证。')
        print(f'自检通过：Python {sys.version.split()[0]} / numpy {numpy.__version__} / scipy {scipy.__version__}')
        print(f'配置可读；端口 {port}；未连接模拟器。')
        return 0
    print(f'问题4研究策略 {VERSION} / {args.policy} | 端口 {port}')
    print('这是第四问覆盖改进版研究候选，尚无官方演练成绩。')
    print('请在模拟器选择【问题4演练测试】，开始后等待“接口已就绪/等待机器狗进入”。')
    print('接口无法查询演练/正式模式，程序按问题4混合全向/定向干扰器规则工作。')
    input('界面就绪后按 Enter 开始：')
    folder = ROOT / 'runs' / (dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    robot = Robot(team, f'http://127.0.0.1:{port}', folder)
    planner = Planner(robot, policy=args.policy)
    snapshot = folder / 'source_snapshot'
    snapshot.mkdir()
    hashes = {}
    for p in list(ROOT.glob('*.py')) + [p for p in ROOT.glob('*.json') if p.name != 'config.json']:
        shutil.copy2(p, snapshot / p.name)
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (folder / 'manifest.json').write_text(json.dumps(dict(strategy=VERSION, policy=args.policy, policy_parameters=POLICIES[args.policy],
        python=sys.version, numpy=numpy.__version__, scipy=scipy.__version__, shapely=shapely.__version__, source_sha256=hashes,
        config_path=str(config_path), mode='user_selected_P4_practice_not_API_verified'),
        ensure_ascii=False, indent=2), encoding='utf-8')
    outcome, error_text, entered = 'completed', None, False
    robot.started = time.monotonic()
    try:
        robot.call('/enter')
        entered = True
        planner.run()
    except BudgetReached as error:
        outcome, error_text = 'budget_stop', str(error)
    except (Exception, KeyboardInterrupt) as error:
        outcome, error_text = 'error', str(error) or '用户中断'
        # Interruption during HTTP could leave execution state unknown.
        if isinstance(error, KeyboardInterrupt):
            robot.transport_uncertain = True
    finally:
        if entered and not robot.transport_uncertain:
            try:
                robot.call('/exit')
            except Exception as error:
                outcome = 'exit_unconfirmed'
                error_text = (error_text or '') + '\n退出未确认：' + str(error)
        count = len(robot.cleared)
        summary = dict(strategy=VERSION, policy=args.policy, policy_parameters=POLICIES[args.policy], outcome=outcome, error=error_text,
            exit_confirmed=robot.exit_confirmed, transport_uncertain=robot.transport_uncertain,
            cleared_count=count, cleared_channels=sorted(robot.cleared),
            observed_but_uncleared=sorted(robot.discovered - robot.cleared),
            measure_count=robot.measure_count, clear_failures=robot.clear_failures,
            scanned_sites=robot.scanned_sites, distance_m=robot.distance_m, switches=robot.switches,
            virtual_time_s=robot.virtual, average_clear_time_s=robot.virtual / count if count else None,
            local_elapsed_s=time.monotonic() - robot.started,
            actual_jammer_count=None, completion=planner.certificate(),
            note='实际目标总数和正式成绩以模拟器为准；完整性证书以问题4半圆定向/全向与R≥1000规则为前提。')
        (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        robot.log.close()
        print(f'\n结束：清除 {count} 个；虚拟时间 {robot.virtual:.1f} 秒；移动 {robot.distance_m:.1f} 米。')
        print(f'状态 {outcome}；退出确认 {robot.exit_confirmed}；结束依据 {planner.stop_reason}')
        if error_text:
            print(error_text)
        print(f'运行记录：{folder}')
        print('请保存模拟器结束界面、案例编码、实际目标数，并导出官方 .jlog。')
    return 0 if outcome == 'completed' and robot.exit_confirmed else 1


if __name__ == '__main__':
    sys.exit(main())
