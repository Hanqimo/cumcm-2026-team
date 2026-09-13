"""Round 2: route and search/localization integration; frozen M03 base."""
from pathlib import Path
import json, math, time, argparse, hashlib, sys, platform
import numpy as np
import base
MODEL = Path(__file__).resolve().parents[1]
RING = json.loads(Path(__file__).with_name('ring.json').read_text(encoding='utf8'))
SITES = np.array(RING['points'])
NAMES = {'E0': '原E最近邻', 'R': '开放路线优化', 'J': '顺路定位', 'RJ': '路线与定位融合', 'JD': '只推迟不顺路补测', 'J100': '顺路定位100m', 'J500': '顺路定位500m', 'K': '可见性检查后顺路定位'}

def length(p, route, sites):
    return float(np.linalg.norm(np.diff(np.vstack([p, sites[route]]), axis=0), axis=1).sum()) if route else 0.0

def open_route(p, ids, sites, opt=True):
    todo = set(ids)
    r = []
    q = p
    while todo:
        i = min(todo, key=lambda i: (np.linalg.norm(sites[i] - q), i))
        r.append(i)
        todo.remove(i)
        q = sites[i]
    if not opt:
        return r
    best = length(p, r, sites)
    for repeat in range(30):
        improved = False
        for i in range(len(r) - 1):
            for j in range(i + 1, len(r)):
                rr = r[:i] + r[i:j + 1][::-1] + r[j + 1:]
                value = length(p, rr, sites)
                if value < best - 1e-07:
                    r = rr
                    best = value
                    improved = True
        if not improved:
            break
    return r

class Integrated(base.Planner):

    def __init__(self, robot, variant):
        super().__init__(robot, 'heading', SITES.copy())
        self.name = variant
        self.deferred = 0
        self.shared_measures = 0

    def route(self, remaining):
        return open_route(self.robot.position, remaining, self.sites, self.name in ['R', 'RJ'])

    def share_worth(self, t, q):
        if t.radius <= 19.5:
            return False
        if any((math.dist(q, h['point']) <= 2 for h in t.history)):
            return False
        d = math.dist(q, t.center)
        if d > 1200:
            return False
        old = np.array(t.positive[-1]['point'])
        u = old - t.center
        v = q - t.center
        angle = math.degrees(math.acos(float(np.clip(u @ v / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-10), -1, 1))))
        return angle >= 15 or d < 0.7 * np.linalg.norm(u)

    def future_useful(self, t, route):
        (g, r, n) = base.heading_hypotheses(t)
        if not len(g):
            return False
        for i in route[:3]:
            q = self.sites[i]
            if not self.share_worth(t, q):
                continue
            delta = q - g
            visible = (np.linalg.norm(delta, axis=1) <= r) & ((delta * n).sum(axis=1) >= -1e-08)
            if float(visible.mean()) >= 0.7:
                return True
        return False

    def run(self):
        remaining = set(range(len(self.sites)))
        joint = self.name in ['J', 'RJ', 'JD', 'J100', 'J500', 'K']
        detour_limit = {'J100': 100, 'J500': 500}.get(self.name, 250)
        while remaining:
            route = self.route(remaining)
            i = route[0]
            q = self.sites[i]
            remaining.remove(i)
            channels = [ch for ch in range(1, 21) if ch not in self.tracks]
            if joint and self.name != 'JD':
                channels += [ch for (ch, t) in sorted(self.tracks.items()) if ch not in self.robot.cleared and self.share_worth(t, q)]
            channels = sorted(channels)
            for ch in channels:
                if ch in self.tracks:
                    self.shared_measures += 1
                self.observe(q, ch)
            self.visited.add(i)
            self.scan_history.append(dict(site=i, point=q.tolist(), channels=channels))
            self.robot.record(dict(kind='scan_site', site=i, channels=channels))
            while any((ch not in self.robot.cleared for ch in self.tracks)):
                p = self.robot.position
                pending = [ch for ch in self.tracks if ch not in self.robot.cleared]
                next_route = self.route(remaining)
                next_q = self.sites[next_route[0]] if next_route else None
                costs = {}
                for ch in pending:
                    t = self.tracks[ch]
                    d = math.dist(p, t.center)
                    detour = d if next_q is None else d + math.dist(t.center, next_q) - math.dist(p, next_q)
                    costs[ch] = (detour, d)
                ch = min(pending, key=lambda ch: (costs[ch][0], costs[ch][1], ch)) if joint else min(pending, key=lambda ch: (math.dist(p, self.tracks[ch].center), ch))
                (detour, d) = costs[ch]
                if joint and remaining and (len(self.tracks) < 16) and (detour > detour_limit) and (d > 350):
                    if self.name != 'K' or self.future_useful(self.tracks[ch], next_route):
                        self.deferred += len(pending)
                        self.robot.record(dict(kind='defer', channels=pending, next_site=next_route[0], detour_m=detour, distance_m=d))
                        break
                    self.robot.record(dict(kind='defer_rejected', channel=ch, reason='no useful visible station in next three'))
                self.solve(ch)
            if len(self.robot.cleared) == 16:
                return 'count upper bound'
        while any((ch not in self.robot.cleared for ch in self.tracks)):
            ch = min((ch for ch in self.tracks if ch not in self.robot.cleared), key=lambda ch: math.dist(self.robot.position, self.tracks[ch].center))
            self.solve(ch)
        for ch in range(1, 21):
            if ch not in self.tracks:
                assert len(self.negatives[ch]) == len(self.sites)
        return 'mesh certificate and all discovered cleared'
