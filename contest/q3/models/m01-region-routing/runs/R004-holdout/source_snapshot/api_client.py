"""Serial, idempotent simulator client. No network calls on import."""
import datetime as dt
from http.client import HTTPException
import json
import math
from pathlib import Path
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


class BudgetReached(Exception):
    pass


class Robot:
    def __init__(self, team, url, directory):
        self.team, self.url = team, url.rstrip('/')
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.log = (self.directory / 'actions.jsonl').open('w', encoding='utf-8')
        self.opener = build_opener(ProxyHandler({}))
        self.prefix, self.sequence = uuid.uuid4().hex[:12], 0
        self.virtual, self.deadline = 0., float('inf')
        self.started = None
        self.exit_confirmed = self.transport_uncertain = False
        self.cleared, self.discovered = set(), set()
        self.measure_count = self.clear_failures = self.scanned_sites = 0
        self.position, self.channel = (0., 0.), 1
        self.distance_m = 0.
        self.switches = 0

    def record(self, value):
        self.log.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        self.log.flush()

    def check_budget(self):
        if time.monotonic() > self.deadline - 20 or self.virtual > 349000:
            raise BudgetReached('接近运行时间上限，保留退出余量')
        if self.transport_uncertain:
            raise RuntimeError('上一动作是否执行尚不确定，停止发送新动作')

    def call(self, path, **fields):
        if self.transport_uncertain:
            raise RuntimeError('上一动作执行状态不确定，不能发送新请求')
        if path != '/exit':
            self.check_budget()
        self.sequence += 1
        payload = dict(arena_id='default', robot_id=self.team,
                       request_id=f'{self.prefix}-{self.sequence}', **fields)
        body = json.dumps(payload, allow_nan=False).encode('utf-8')
        for attempt in range(1, 4):
            self.record(dict(kind='request', time=dt.datetime.now().isoformat(), path=path,
                             attempt=attempt, payload=payload))
            try:
                req = Request(self.url + path, data=body,
                              headers={'Content-Type': 'application/json'}, method='POST')
                try:
                    with self.opener.open(req, timeout=4) as response:
                        status, raw = response.status, response.read()
                except HTTPError as error:
                    status, raw = error.code, error.read()
                if status >= 500:
                    raise ConnectionError(f'HTTP {status}: action state uncertain')
                data = json.loads(raw.decode('utf-8'))
                self.record(dict(kind='response', request_id=payload['request_id'],
                                 http_status=status, response=data))
                if not isinstance(data, dict) or 'accepted' not in data:
                    raise ValueError('接口响应缺少 accepted 字段')
                if status != 200 or data['accepted'] is not True:
                    # Explicit rejection is definite; its zero clock is not a reset.
                    raise RuntimeError(f'{path} 未接受：HTTP {status}，{data}')
                virtual = float(data['virtual_time_s'])
                if not math.isfinite(virtual) or virtual < self.virtual - 1e-5:
                    raise ValueError('接口时钟无效或倒退')
                if path == '/measure':
                    if data.get('measure_result') not in ('no_signal', 'near', 'direction'):
                        raise ValueError('无效测量结果')
                    if data['measure_result'] == 'direction' and not math.isfinite(float(data['svd_deg'])):
                        raise ValueError('无效示向度')
                if path == '/clear' and data.get('clear_result') not in ('success', 'no_target_in_range'):
                    raise ValueError('无效清除结果')
                if path == '/enter':
                    remaining = float(data['remaining_real_duration_s'])
                    if not math.isfinite(remaining) or remaining < 0:
                        raise ValueError('无效剩余时间')
                    self.deadline = self.started + min(remaining, 1200.)
                self.virtual = virtual
                if path == '/exit':
                    self.exit_confirmed = True
                return data
            except (URLError, TimeoutError, ConnectionError, OSError, HTTPException,
                    ValueError, KeyError, TypeError) as error:
                self.record(dict(kind='uncertain_response', attempt=attempt, error=str(error)))
                if attempt == 3:
                    self.transport_uncertain = True
                    raise RuntimeError('同一请求重试仍未确认；已停止新动作，请查看模拟器和日志') from error
                time.sleep(.25)

    def _move(self, point):
        self.distance_m += math.dist(self.position, point)
        self.position = tuple(point)

    def measure(self, point, channel):
        data = self.call('/measure', position={'x': float(point[0]), 'y': float(point[1])}, channel=channel)
        self._move(point)
        self.switches += int(channel != self.channel)
        self.channel = channel
        self.measure_count += 1
        if data['measure_result'] != 'no_signal':
            self.discovered.add(channel)
        return data

    def clear(self, point, channel):
        data = self.call('/clear', position={'x': float(point[0]), 'y': float(point[1])}, channel=channel)
        self._move(point)
        success = data['clear_result'] == 'success'
        if success:
            self.cleared.add(channel)
            print(f'  清除频道 {channel:2d}；累计 {len(self.cleared)} 个；虚拟时间 {self.virtual:.1f} 秒', flush=True)
        else:
            self.clear_failures += 1
        # /clear does not change the measurement channel.
        return success
