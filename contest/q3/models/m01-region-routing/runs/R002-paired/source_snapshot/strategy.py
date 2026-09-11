"""P3 M01/A01 v1: bounded-bearing regions, local routing, certified search.

No simulator connection at import; coordinates metres, angles degrees.
Heuristic efficiency; safety checks use outer regions, not point estimates.
"""
import math
import numpy as np
from bearing_geometry import (outer_disk, disk_halfplanes, wedge,
                              clip_halfplanes, enclosing_circle, diameter)

VERSION = 'p3-region-routing-v1'
EPS = 1.0051  # bounded error plus 0.005 degree rounding and numerical margin
CLEAR_RADIUS = 19.5
SIDES = 180


def scan_sites():
    return [(0., 0.)] + [(1350 * math.cos(i * math.pi / 3),
                         1350 * math.sin(i * math.pi / 3)) for i in range(6)]


class Coverage:
    """Whole-square coverage certificate of the continuous 1800 m arena.

    Keep EVERY square intersecting the arena, including boundary squares.
    no_signal implies exclusion of the closed 1000 m disk for P3 only.
    Cover a square only if its farthest corner is within 999.99 m.
    """
    def __init__(self, level=7):
        self.level = level
        self.half = 1800 / 2 ** level
        axis = np.linspace(-1800 + self.half, 1800 - self.half, 2 ** level)
        x, y = np.meshgrid(axis, axis)
        centers = np.column_stack((x.ravel(), y.ravel()))
        nearest = np.maximum(np.abs(centers) - self.half, 0)
        self.centers = centers[np.sum(nearest ** 2, axis=1) <= 1800 ** 2 + 1e-6]
        self.covered = np.zeros((21, len(self.centers)), dtype=bool)
        self.samples = {c: [] for c in range(1, 21)}

    def mask(self, point):
        far = np.abs(self.centers - np.asarray(point)) + self.half
        return np.sum(far ** 2, axis=1) <= 999.99 ** 2

    def add(self, channel, point):
        self.covered[channel] |= self.mask(point)
        self.samples[channel].append([float(v) for v in point])

    def absent(self, channel):
        return bool(np.all(self.covered[channel]))

    def gain(self, point, channels):
        if not channels:
            return 0.
        return float(np.mean((~self.covered[channels]) & self.mask(point)))


class Track:
    def __init__(self, channel):
        self.channel = channel
        self.poly = outer_disk((0, 0), 1800, SIDES)
        self.history = []
        self.center = None
        self.radius = float('inf')

    def update(self, point, observation):
        kind = observation['measure_result']
        if kind == 'no_signal':
            return  # Disk exclusion is nonconvex; do not cut it incorrectly.
        if kind not in ('near', 'direction'):
            raise ValueError(f'Unknown measure_result: {kind}')
        poly = self.poly
        if kind == 'direction':
            A, b = wedge(point, float(observation['svd_deg']), EPS)
            poly = clip_halfplanes(poly, A, b)
        A, b = disk_halfplanes(point, 5.000001 if kind == 'near' else 1500.000001, SIDES)
        poly = clip_halfplanes(poly, A, b)
        if not len(poly):
            raise ArithmeticError(f'频道 {self.channel} 观测区域为空；保留日志后退出，不能据此清除')
        self.poly = poly
        self.center, self.radius, _ = enclosing_circle(poly)
        self.history.append(dict(position=[float(v) for v in point], **observation))

    def safe_clear_point(self, position):
        """Nearest safe point along center->robot segment (not global projection)."""
        if self.radius > CLEAR_RADIUS:
            return None
        c, p = self.center, np.asarray(position, float)
        if np.max(np.linalg.norm(self.poly - p, axis=1)) <= CLEAR_RADIUS:
            return p.copy()
        low, high = 0., 1.
        for _ in range(45):
            t = (low + high) / 2
            q = c + t * (p - c)
            if np.max(np.linalg.norm(self.poly - q, axis=1)) <= CLEAR_RADIUS:
                low = t
            else:
                high = t
        return c + low * (p - c)

    def next_point(self, position):
        """Move toward the region with a bounded cross-bearing offset.

        If every possible source is <= 1000 m away, reception is guaranteed.
        Also recognize Q2's first-observation safe lens, valid even if a
        source's first distance was > 1000 m. The lens is a sufficient test.
        """
        c, r = self.center, self.radius
        if r <= 120:
            candidates = [c]
        else:
            _, (i, j) = diameter(self.poly)
            d = self.poly[j] - self.poly[i]
            normal = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-12)
            offset = min(150., r * .25)
            candidates = [c + offset * normal, c - offset * normal]
        first = self.history[0]
        s = np.asarray(first['position'])
        safe = []
        for q in candidates:
            all_close = np.max(np.linalg.norm(self.poly - q, axis=1)) <= 999.9
            in_lens = False
            if first['measure_result'] == 'direction':
                a = math.radians(float(first['svd_deg']))
                u, v = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
                ab = np.array([np.dot(q - s, u), np.dot(q - s, v)])
                ep = math.radians(EPS)
                length2 = float(np.dot(ab, ab))
                in_lens = (length2 <= 1000 ** 2 - 1e-3 and
                           length2 <= 2000 * (ab[0] * math.cos(ep) - abs(ab[1]) * math.sin(ep)) - 1e-3)
            if all_close or in_lens:
                safe.append(q)
        # Region fits a disk of radius < 1000 after one direction report.
        if not safe:
            if r > 999.9:
                raise ArithmeticError('未找到可证明接收的下一观测点')
            safe = [c]
        q = min(safe, key=lambda p: float(np.linalg.norm(p - position)))
        # Same-coordinate noise is fixed: never repeat an uninformative point.
        if any(math.dist(q, h['position']) < .1 for h in self.history):
            _, (i, j) = diameter(self.poly)
            d = self.poly[j] - self.poly[i]
            normal = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-12)
            alternates = [c + normal * 40, c - normal * 40]
            safe = [p for p in alternates if np.max(np.linalg.norm(self.poly - p, axis=1)) <= 999.9]
            if not safe:
                raise ArithmeticError('重复观测点且没有安全侧移点')
            q = min(safe, key=lambda p: float(np.linalg.norm(p - position)))
        return np.asarray(q)


class Planner:
    def __init__(self, robot, *, opportunistic=True, nearest_order=True):
        self.robot = robot
        self.coverage = Coverage()
        self.tracks = {}
        self.anchors = scan_sites()
        self.opportunistic = opportunistic
        self.nearest_order = nearest_order
        self.stop_reason = None

    def unknown(self):
        return [c for c in range(1, 21) if c not in self.robot.discovered
                and not self.coverage.absent(c)]

    def observe(self, point, channel):
        p = tuple(float(v) for v in point)
        observation = self.robot.measure(p, channel)
        if observation['measure_result'] == 'no_signal':
            self.coverage.add(channel, p)
        else:
            track = self.tracks.setdefault(channel, Track(channel))
            track.update(p, observation)
            self.robot.record(dict(kind='region', channel=channel, position=list(p),
                                   radius_m=track.radius, center=track.center.tolist(),
                                   vertices=track.poly.tolist(), observations=len(track.history)))
        return observation

    def scan(self, point, full=False):
        unknown = self.unknown()
        scan_unknown = full or self.coverage.gain(point, unknown) >= .05
        channels = set(unknown if scan_unknown else [])
        for c, track in self.tracks.items():
            if c in self.robot.cleared:
                continue
            if full or (track.radius > CLEAR_RADIUS and
                        math.dist(point, track.history[-1]['position']) >= 200 and
                        np.max(np.linalg.norm(track.poly - point, axis=1)) <= 999.9):
                channels.add(c)
        if channels:
            self.robot.scanned_sites += 1
        # Start with current measurement channel if possible. Clear does not switch it.
        for c in sorted(channels, key=lambda c: (c != self.robot.channel, c)):
            self.observe(point, c)

    def solve_track(self, track):
        for _ in range(16):
            self.robot.check_budget()
            q = track.safe_clear_point(self.robot.position)
            if q is not None:
                bound = float(np.max(np.linalg.norm(track.poly - q, axis=1)))
                self.robot.record(dict(kind='clear_certificate', channel=track.channel,
                                       point=q.tolist(), worst_distance_m=bound))
                if not self.robot.clear(tuple(float(v) for v in q), track.channel):
                    raise ArithmeticError('有界误差清除证书与接口失败冲突；请保留记录检查')
                return
            q = track.next_point(np.asarray(self.robot.position))
            observation = self.observe(q, track.channel)
            if observation['measure_result'] == 'no_signal':
                raise ArithmeticError('保证接收点返回无信号；检查问题模式、参数和角度约定')
        raise RuntimeError(f'频道 {track.channel} 达到 16 次定位预算，仍未达到可靠清除精度')

    def run(self):
        self.scan(self.anchors.pop(0), full=True)
        while True:
            self.robot.check_budget()
            pending = [t for c, t in self.tracks.items() if c not in self.robot.cleared]
            if pending:
                def score(t):
                    q = t.safe_clear_point(self.robot.position)
                    q = t.center if q is None else q
                    return math.dist(q, self.robot.position) + .15 * t.radius
                track = min(pending, key=score if self.nearest_order else lambda t: t.channel)
                self.solve_track(track)
                if len(self.robot.cleared) < 16 and self.opportunistic:
                    self.scan(self.robot.position)
                continue
            if len(self.robot.cleared) == 16:
                self.stop_reason = 'cleared_upper_bound_16'
                break
            unknown = self.unknown()
            if not unknown:
                self.stop_reason = 'continuous_coverage_certificate'
                break
            if not self.anchors:
                raise RuntimeError('七点扫描后仍有频道未被覆盖证书排除；不能声称全部清除')
            site = min(self.anchors, key=lambda p: (math.dist(p, self.robot.position) + 100) /
                       max(self.coverage.gain(p, unknown), 1e-6))
            self.anchors.remove(site)
            self.scan(site, full=True)
        self.robot.record(dict(kind='completion_certificate', **self.certificate()))
        return self.stop_reason

    def certificate(self):
        absent = [c for c in range(1, 21) if c not in self.robot.discovered and self.coverage.absent(c)]
        return dict(stop_reason=self.stop_reason, grid_level=self.coverage.level,
                    square_side_m=self.coverage.half * 2, square_count=len(self.coverage.centers),
                    absent_channels=absent, cleared_channels=sorted(self.robot.cleared),
                    no_signal_positions={str(c): self.coverage.samples[c] for c in absent})
