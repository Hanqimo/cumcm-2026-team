"""问题3流程体验策略；只依赖 Python 标准库。"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent


class BudgetReached(Exception):
    pass


class Robot:
    def __init__(self, team, url, directory):
        self.team = team
        self.url = url.rstrip('/')
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.log = (directory / 'actions.jsonl').open('w', encoding='utf-8')
        self.opener = build_opener(ProxyHandler({}))
        self.prefix = uuid.uuid4().hex[:12]
        self.sequence = 0
        self.virtual = 0.0
        self.deadline = float('inf')
        self.started = None
        self.exit_confirmed = False
        self.cleared = set()
        self.discovered = set()
        self.measure_count = 0
        self.clear_failures = 0
        self.scanned_sites = 0
        self.transport_uncertain = False

    def record(self, value):
        self.log.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        self.log.flush()

    def call(self, path, **fields):
        if path != '/exit' and (time.monotonic() > self.deadline - 15 or self.virtual > 350000):
            raise BudgetReached('接近运行时间上限，准备退出')
        self.sequence += 1
        payload = dict(arena_id='default', robot_id=self.team,
                       request_id=f'{self.prefix}-{self.sequence}', **fields)
        body = json.dumps(payload, allow_nan=False).encode('utf-8')
        # 每次重试保留相同字节与 ID，防止重复执行动作。
        for attempt in range(1, 4):
            self.record(dict(kind='request', time=dt.datetime.now().isoformat(),
                             path=path, attempt=attempt, payload=payload))
            try:
                req = Request(self.url + path, data=body,
                              headers={'Content-Type': 'application/json'}, method='POST')
                try:
                    with self.opener.open(req, timeout=4) as response:
                        status, raw = response.status, response.read()
                except HTTPError as error:
                    status, raw = error.code, error.read()
                data = json.loads(raw.decode('utf-8'))
                self.record(dict(kind='response', request_id=payload['request_id'],
                                 http_status=status, response=data))
                if status != 200 or data.get('accepted') is not True:
                    raise RuntimeError(f'{path} 未被接受：HTTP {status}，{data}')
                self.virtual = float(data['virtual_time_s'])
                if path == '/enter':
                    # 请求前的时间作为保守起点，避免把重试耗时加到服务器限时上。
                    self.deadline = self.started + int(data['remaining_real_duration_s'])
                elif path == '/exit':
                    self.exit_confirmed = True
                return data
            except (URLError, TimeoutError, ConnectionError, OSError) as error:
                self.record(dict(kind='network_error', attempt=attempt, error=str(error)))
                if attempt == 3:
                    self.transport_uncertain = True
                    raise RuntimeError('接口无法连接或响应中断；请查看模拟器状态和日志。') from error
                time.sleep(0.5)

    def measure(self, point, channel):
        data = self.call('/measure', position={'x': point[0], 'y': point[1]}, channel=channel)
        self.measure_count += 1
        if data['measure_result'] != 'no_signal':
            self.discovered.add(channel)
        return data

    def clear(self, point, channel):
        data = self.call('/clear', position={'x': point[0], 'y': point[1]}, channel=channel)
        success = data['clear_result'] == 'success'
        if success:
            self.cleared.add(channel)
            print(f'  已清除频道 {channel:2d}；累计 {len(self.cleared)} 个；虚拟时间 {self.virtual:.1f} 秒', flush=True)
        else:
            self.clear_failures += 1
        return success


def scan_sites():
    # 中心 + 半径 1350 m 的正六边形顶点，覆盖半径 1800 m 圆域。
    return [(0.0, 0.0)] + [(1350 * math.cos(i * math.pi / 3),
                            1350 * math.sin(i * math.pi / 3)) for i in range(6)]


def follow_bearing(robot, point, channel, observation):
    """固定步长沿示向度走；发生大转向时减半，最多24步。"""
    step = 250.0
    previous_angle = None
    for _ in range(24):
        result = observation['measure_result']
        if result == 'no_signal':
            return False
        if result == 'near':
            return robot.clear(point, channel)
        angle = math.radians(observation['svd_deg'])
        if previous_angle is not None and math.cos(angle - previous_angle) < 0:
            step = max(7.8125, step / 2)
        if step <= 31.25 and robot.clear(point, channel):
            return True
        point = (point[0] + step * math.cos(angle), point[1] + step * math.sin(angle))
        previous_angle = angle
        observation = robot.measure(point, channel)
    # 循环上限时只在最后检测位置再尝试一次，不宣称一定成功。
    return robot.clear(point, channel)


def run_strategy(robot):
    for index, site in enumerate(scan_sites(), 1):
        print(f'扫描点 {index}/7：({site[0]:.0f}, {site[1]:.0f})', flush=True)
        observations = []
        # 先在同一点完成扫描，避免每检测一个频道就来回跑。
        for channel in range(1, 21):
            if channel in robot.cleared:
                continue
            observation = robot.measure(site, channel)
            if observation['measure_result'] != 'no_signal':
                observations.append((channel, observation))
        robot.scanned_sites += 1
        for channel, observation in observations:
            print(f'  追踪频道 {channel} …', flush=True)
            follow_bearing(robot, site, channel, observation)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--team', help='默认读取 config.json 中的参赛队号')
    parser.add_argument('--port', type=int, help='默认读取 config.json 中的端口')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    team = args.team or config['team_no']
    port = args.port or config['port']
    print(f'问题3演练流程体验 | 队号 {team} | 本机端口 {port}')
    print('请在模拟器选择【问题3演练测试】，开始后等待“接口已就绪/等待机器狗进入”。')
    print('接口不提供演练/正式模式查询，请确认界面选择的是演练。')
    input('准备好后按 Enter 运行；尚未就绪可先保持本窗口等待：')
    folder = ROOT / 'runs' / (dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    robot = Robot(team, f'http://127.0.0.1:{port}', folder)
    outcome, error_text = 'completed', None
    entered = False
    try:
        robot.started = time.monotonic()
        robot.call('/enter')
        entered = True
        run_strategy(robot)
    except BudgetReached as error:
        outcome, error_text = 'budget_stop', str(error)
    except (Exception, KeyboardInterrupt) as error:
        outcome, error_text = 'error', str(error) or '用户中断'
    finally:
        if entered and not robot.transport_uncertain:
            try:
                robot.call('/exit')
            except Exception as error:
                outcome = 'exit_unconfirmed'
                error_text = (error_text or '') + '\n退出未确认：' + str(error)
        count = len(robot.cleared)
        summary = dict(strategy='p3-seven-sites-bearing-pursuit-v1', outcome=outcome,
                       error=error_text, exit_confirmed=robot.exit_confirmed,
                       scanned_sites=robot.scanned_sites,
                       cleared_count=count, cleared_channels=sorted(robot.cleared),
                       observed_but_uncleared=sorted(robot.discovered - robot.cleared),
                       measure_count=robot.measure_count, clear_failures=robot.clear_failures,
                       virtual_time_s=robot.virtual,
                       average_clear_time_s=robot.virtual / count if count else None,
                       local_elapsed_s=round(time.monotonic() - robot.started, 3),
                       actual_jammer_count=None,
                       note='实际目标总数及程序运行时间以模拟器结束界面为准；完成扫描不等同于全部清除。')
        (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        robot.log.close()
        print(f'\n运行结束：清除 {count} 个，虚拟耗时 {robot.virtual:.1f} 秒。')
        print(f'主动退出已确认：{robot.exit_confirmed}；运行状态：{outcome}')
        if error_text:
            print(error_text)
        print(f'可读日志和摘要：{folder}')
        print('请查看模拟器结果、记下案例编码和实际目标数量，并导出该局官方 .jlog。')
    return 0 if outcome == 'completed' and robot.exit_confirmed else 1


if __name__ == '__main__':
    sys.exit(main())
