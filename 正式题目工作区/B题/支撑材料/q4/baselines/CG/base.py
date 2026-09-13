"""Fresh Q4 prototypes. No imports from any previous Q4 strategy.

Only Q1 geometry is reused. Physics hides truth behind the Robot facade.
All strategies share a proved discovery mesh and a finite optical fallback.
"""
from pathlib import Path
import sys, math, json, argparse, time, hashlib, platform
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from scipy.spatial import Delaunay
MODEL = Path(__file__).resolve().parents[1]
ROOT = MODEL
from bearing_geometry import outer_disk, clip_halfplanes, wedge, enclosing_circle, diameter, unit
EPS = 1.0051
SPACING = 980.0
NAMES = {'staged': 'A 先搜后清', 'interleave': 'B 边搜边清', 'heading': 'C 朝向情景选点', 'optical': 'D 朝向选点加光学捷径', 'ring': 'E 环带围合加朝向选点'}

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)

def mesh():
    mapping = {}
    faces = []
    for i in range(-5, 5):
        for j in range(-5, 5):
            for ids in [[(i, j), (i + 1, j), (i, j + 1)], [(i + 1, j), (i + 1, j + 1), (i, j + 1)]]:
                vs = np.array([[SPACING * (x + 0.5 * y), SPACING * math.sqrt(3) / 2 * y] for (x, y) in ids])
                if Polygon(vs).distance(Point(0, 0)) <= 1800.0:
                    faces.append(ids)
                    for (key, v) in zip(ids, vs):
                        mapping[key] = v
    keys = sorted(mapping)
    pts = np.array([mapping[k] for k in keys])
    idx = {k: i for (i, k) in enumerate(keys)}
    tri = [[idx[k] for k in face] for face in faces]
    return (pts, tri)
(SITES, FACES) = mesh()

class Track:

    def __init__(self, ch):
        self.channel = ch
        self.region = None
        self.history = []
        self.positive = []
        self.center = None
        self.radius = np.inf
        self.poly = None

    def refresh(self):
        if self.region.is_empty:
            raise ArithmeticError('empty outer position set')
        self.poly = np.array(self.region.convex_hull.exterior.coords[:-1])
        (self.center, self.radius, _) = enclosing_circle(self.poly)

    def update(self, q, z):
        self.history.append(dict(point=np.asarray(q).tolist(), **z))
        if z['measure_result'] == 'no_signal':
            return
        self.positive.append(self.history[-1])
        rad = 5.0 if z['measure_result'] == 'near' else 1500.0
        new = outer_disk(q, rad, 144 if rad > 5 else 32)
        if z['measure_result'] == 'direction':
            new = clip_halfplanes(new, *wedge(q, z['svd_deg'], EPS))
        g = Polygon(new).intersection(Polygon(outer_disk([0, 0], 1800, 144)))
        self.region = g if self.region is None else self.region.intersection(g)
        self.refresh()

    def exclude(self, q):
        self.region = self.region.difference(Point(*q).buffer(19.999, quad_segs=24))
        self.refresh()

def samples(track):
    p = track.poly
    c = np.array(track.region.representative_point().coords[0])
    (_, (i, j)) = diameter(p)
    candidates = [c, *[0.9 * ((1 - f) * p[i] + f * p[j]) + 0.1 * c for f in np.linspace(0, 1, 9)]]
    candidates += [0.95 * x + 0.05 * c for x in p]
    keep = []
    for x in candidates:
        if track.region.covers(Point(*x)) and all((np.linalg.norm(x - y) > 0.0001 for y in keep)):
            keep.append(x)
    return np.array(keep[:16])

def heading_hypotheses(track):
    g = samples(track)
    positions = np.repeat(g, 3 * 25, axis=0)
    radii = np.tile(np.repeat([1000.0, 1250.0, 1500.0], 25), len(g))
    normals = np.tile(np.vstack([np.zeros(2), np.c_[np.cos(np.arange(24) * np.pi / 12), np.sin(np.arange(24) * np.pi / 12)]]), (len(g) * 3, 1))
    good = np.ones(len(positions), dtype=bool)
    for h in track.history:
        delta = np.asarray(h['point']) - positions
        d = np.linalg.norm(delta, axis=1)
        visible = (delta * normals).sum(axis=1) >= -1e-08
        heard = (d <= radii + 1e-06) & visible
        if h['measure_result'] == 'no_signal':
            good &= ~heard
        else:
            good &= heard
            if h['measure_result'] == 'near':
                good &= d <= 5.001
            else:
                good &= d > 4.999
    return (positions[good], radii[good], normals[good])

class Planner:

    def __init__(self, robot, variant, sites=None):
        self.sites = SITES if sites is None else np.asarray(sites, float)
        self.robot = robot
        self.variant = variant
        self.tracks = {}
        self.negatives = {ch: [] for ch in range(1, 21)}
        self.visited = set()
        self.scan_history = []
        self.hyp_empty = 0
        self.fallbacks = 0
        self.lost = 0

    def observe(self, q, ch):
        z = self.robot.measure(q, ch)
        if ch not in self.tracks and z['measure_result'] != 'no_signal':
            t = Track(ch)
            t.history = list(self.negatives[ch])
            self.tracks[ch] = t
        if ch in self.tracks:
            self.tracks[ch].update(q, z)
            t = self.tracks[ch]
            self.robot.record(dict(kind='region', channel=ch, wkt=t.region.wkt, radius_m=t.radius))
        elif z['measure_result'] == 'no_signal':
            self.negatives[ch].append(dict(point=np.asarray(q).tolist(), **z))
        return z

    def try_clear(self, t, q, reason):
        self.robot.record(dict(kind='clear_reason', channel=t.channel, reason=reason, radius_m=t.radius))
        ok = self.robot.clear(q, t.channel)
        if not ok:
            t.exclude(q)
        return ok

    def candidates(self, t):
        p = self.robot.position
        c = t.center
        (_, (i, j)) = diameter(t.poly)
        u = t.poly[j] - t.poly[i]
        u = u / max(np.linalg.norm(u), 1e-12)
        v = np.array([-u[1], u[0]])
        off = max(25.0, min(220.0, t.radius * 0.5))
        raw = [c + off * v, c - off * v, c]
        for f in [0.4, 0.7]:
            mid = p + f * (c - p)
            raw += [mid, mid + 0.6 * off * v, mid - 0.6 * off * v]
        raw += [c + 0.25 * off * u, c - 0.25 * off * u]
        return [q for q in raw if all((math.dist(q, h['point']) > 2 for h in t.history))]

    def select(self, t):
        candidates = self.candidates(t)
        if not candidates:
            return None
        p = self.robot.position
        if self.variant in ['staged', 'interleave']:
            q = min(candidates[:2], key=lambda q: np.linalg.norm(q - p))
            return q
        (g, rad, n) = heading_hypotheses(t)
        if not len(g):
            self.hyp_empty += 1
            return min(candidates[:2], key=lambda q: np.linalg.norm(q - p))
        scores = []
        for q in candidates:
            delta = q - g
            visible = (np.linalg.norm(delta, axis=1) <= rad) & ((delta * n).sum(axis=1) >= -1e-08)
            prob = float(visible.mean())
            vg = g[visible]
            if len(vg):
                (ug, counts) = np.unique(np.round(vg, 8), axis=0, return_counts=True)
                sizes = []
                for x in ug:
                    d = np.linalg.norm(x - q)
                    if d <= 5:
                        sizes.append(5.0)
                        continue
                    angle = math.degrees(math.atan2(x[1] - q[1], x[0] - q[0]))
                    pp = clip_halfplanes(t.poly, *wedge(q, angle, EPS))
                    sizes.append(enclosing_circle(pp)[1] if len(pp) else t.radius)
                after = float(np.average(sizes, weights=counts))
            else:
                after = t.radius
            cost = np.linalg.norm(q - p) / 5 + 5 + max(0, np.linalg.norm(q - t.center) - 19) / 5
            cost += prob * (after / 5 + 8 * max(0, math.log(max(after / 19, 1), 2)))
            cost += (1 - prob) * (35 + min(t.radius, 350) / 2.5)
            scores.append(float(cost))
        best = int(np.argmin(scores))
        self.robot.record(dict(kind='scenario_choice', channel=t.channel, scenarios=len(g), candidates=[dict(point=q.tolist(), cost_s=sc) for (q, sc) in zip(candidates, scores)], selected=best))
        return candidates[best]

    def optical_cover(self, t):
        self.fallbacks += 1
        step = 25.0
        (xmin, ymin, xmax, ymax) = t.region.bounds
        nodes = []
        for ix in range(math.floor(xmin / step), math.floor(xmax / step) + 1):
            for iy in range(math.floor(ymin / step), math.floor(ymax / step) + 1):
                square = Polygon([(ix * step, iy * step), ((ix + 1) * step, iy * step), ((ix + 1) * step, (iy + 1) * step), (ix * step, (iy + 1) * step)])
                if square.intersects(t.region):
                    nodes.append(np.array([(ix + 0.5) * step, (iy + 0.5) * step]))
        while nodes:
            p = self.robot.position
            i = min(range(len(nodes)), key=lambda i: np.linalg.norm(nodes[i] - p))
            q = nodes.pop(i)
            if not t.region.intersects(Point(*q).buffer(20.01)):
                continue
            if self.try_clear(t, q, 'finite optical cover'):
                return
        raise ArithmeticError('exhausted continuous optical covering without success')

    def solve(self, ch):
        t = self.tracks[ch]
        tries = 0
        for k in range(10):
            if t.radius <= 19.5:
                if not self.try_clear(t, t.center, 'enclosing circle certificate'):
                    raise ArithmeticError('certified clear failed')
                return
            if self.variant == 'optical' and t.radius <= 85 and (tries < 2):
                tries += 1
                q = np.array(t.region.representative_point().coords[0])
                if self.try_clear(t, q, 'optical shortcut'):
                    return
                continue
            q = self.select(t)
            if q is None:
                break
            z = self.observe(q, ch)
            if z['measure_result'] == 'no_signal':
                self.lost += 1
        self.optical_cover(t)

    def run(self):
        remaining = set(range(len(self.sites)))
        while remaining:
            p = self.robot.position
            i = min(remaining, key=lambda i: (np.linalg.norm(self.sites[i] - p), i))
            remaining.remove(i)
            q = self.sites[i]
            to_scan = [ch for ch in range(1, 21) if ch not in self.robot.cleared and (ch not in self.tracks or (self.variant == 'staged' and self.tracks[ch].radius > 19.5))]
            for ch in to_scan:
                self.observe(q, ch)
            self.visited.add(i)
            self.scan_history.append(dict(site=i, point=q.tolist(), channels=to_scan))
            self.robot.record(dict(kind='scan_site', site=i, channels=to_scan))
            if self.variant != 'staged':
                while any((ch not in self.robot.cleared for ch in self.tracks)):
                    ch = min((ch for ch in self.tracks if ch not in self.robot.cleared), key=lambda ch: np.linalg.norm(self.tracks[ch].center - self.robot.position))
                    self.solve(ch)
            if len(self.robot.cleared) == 16:
                return 'count upper bound'
        while any((ch not in self.robot.cleared for ch in self.tracks)):
            ch = min((ch for ch in self.tracks if ch not in self.robot.cleared), key=lambda ch: np.linalg.norm(self.tracks[ch].center - self.robot.position))
            self.solve(ch)
        for ch in range(1, 21):
            if ch not in self.tracks:
                assert len(self.negatives[ch]) == len(self.sites)
        return 'mesh certificate and all discovered cleared'
