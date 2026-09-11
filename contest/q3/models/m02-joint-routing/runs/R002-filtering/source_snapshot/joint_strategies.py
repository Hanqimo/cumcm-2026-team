"""Independent candidate families for P3; all maintain the same clear certificate."""
import math
import numpy as np
from legacy_strategy import Planner as BasePlanner, CLEAR_RADIUS


def open_route(start, points):
    """Nearest-neighbour initialization + open-path 2-opt, fixed start, free end."""
    if not len(points):
        return []
    pts = np.vstack([start, points])
    D = np.linalg.norm(pts[:, None] - pts[None, :], axis=2)
    left = set(range(1, len(pts)))
    route = [0]
    while left:
        q = min(left, key=lambda j: D[route[-1], j])
        route.append(q)
        left.remove(q)
    for _ in range(30):
        gain, best = 1e-8, None
        for i in range(1, len(route) - 1):
            for j in range(i + 1, len(route)):
                old = D[route[i-1], route[i]]
                new = D[route[i-1], route[j]]
                if j + 1 < len(route):
                    old += D[route[j], route[j+1]]
                    new += D[route[i], route[j+1]]
                if old - new > gain:
                    gain, best = old-new, (i, j)
        if best is None:
            break
        i, j = best
        route[i:j+1] = reversed(route[i:j+1])
    return [i-1 for i in route[1:]]


class JointPlanner(BasePlanner):
    def __init__(self, robot, *, family='joint', scan_gain=.05, info_distance=150.,
                 initial_baseline=0., route_on=True, info_radius=60., info_maxobs=2):
        super().__init__(robot)
        self.family = family
        self.scan_gain = scan_gain
        self.info_distance = info_distance
        self.initial_baseline = initial_baseline
        self.route_on = route_on
        self.info_radius = info_radius
        self.info_maxobs = info_maxobs
        self.attempts = {}
        self.iterations = 0

    def observe(self, point, channel):
        result = super().observe(point, channel)
        self.attempts[channel] = tuple(point)
        return result

    def at_site_scan(self, point, force=False):
        """Unknown scans buy coverage; known scans buy intersecting bearings."""
        unknown = self.unknown()
        channels = set(unknown if force or self.coverage.gain(point, unknown) >= self.scan_gain else [])
        for c, track in self.tracks.items():
            if c in self.robot.cleared or track.radius <= self.info_radius or len(track.history) >= self.info_maxobs:
                continue
            if c in self.attempts and math.dist(point,self.attempts[c]) < self.info_distance:
                continue
            if min(math.dist(point, h['position']) for h in track.history) >= self.info_distance:
                # No-signal is allowed for batch measurements; never corrupt P.
                channels.add(c)
        if channels:
            self.robot.scanned_sites += 1
        for c in sorted(channels, key=lambda c: (c != self.robot.channel, c)):
            self.observe(point, c)

    def candidates(self):
        pending = [t for c,t in self.tracks.items() if c not in self.robot.cleared]
        nodes = []
        for t in pending:
            q = t.safe_clear_point(self.robot.position)
            q = t.center if q is None else q
            nodes.append(('target', t.channel, np.asarray(q)))
        unknown = self.unknown()
        if not unknown:
            return nodes
        # Keep a conservative fallback cover from original anchors. We may
        # anticipate target visits for route scoring, but stopping uses real scans.
        covered = self.coverage.covered[unknown[0]].copy()
        if self.family != 'anchors':
            for _, _, q in nodes:
                covered |= self.coverage.mask(q)
        anchors = [(i,p,self.coverage.mask(p)) for i,p in enumerate(self.anchors)]
        needed = []
        while not np.all(covered):
            if not anchors:
                raise RuntimeError('Search fallback cover exhausted')
            # Greedy set cover only selects waypoints; it does not certify absence.
            a = max(anchors, key=lambda a: int(np.count_nonzero(a[2] & ~covered)))
            gain = np.count_nonzero(a[2] & ~covered)
            if not gain:
                raise RuntimeError('No progress in waypoint cover')
            needed.append(('scan', a[0], np.asarray(a[1])))
            covered |= a[2]
            anchors.remove(a)
        return nodes + needed

    def run(self):
        self.at_site_scan((0.,0.), force=True)
        if self.initial_baseline:
            pending = list(self.tracks.values())
            angle = math.atan2(pending[0].center[1], pending[0].center[0]) if pending else 0.
            q = np.array([math.cos(angle),math.sin(angle)]) * self.initial_baseline
            self.at_site_scan(q, force=True)
        # Keep all anchors available; real coverage masks prevent redundant work.
        while True:
            self.iterations += 1
            self.robot.check_budget()
            if self.iterations > 180:
                raise RuntimeError('Joint planner iteration cap')
            pending = [t for c,t in self.tracks.items() if c not in self.robot.cleared]
            if not pending and (len(self.robot.cleared) == 16 or not self.unknown()):
                self.stop_reason = 'cleared_upper_bound_16' if len(self.robot.cleared)==16 else 'continuous_coverage_certificate'
                self.robot.record(dict(kind='completion_certificate', **self.certificate()))
                return self.stop_reason
            self.at_site_scan(self.robot.position)
            nodes = self.candidates()
            if not nodes:
                continue
            order = open_route(self.robot.position, [n[2] for n in nodes]) if self.route_on else sorted(range(len(nodes)),key=lambda i: math.dist(nodes[i][2],self.robot.position))
            kind, c, point = nodes[order[0]]
            if kind == 'scan':
                self.at_site_scan(point, force=True)
            else:
                track = self.tracks[c]
                self.solve_track(track)


class SweepPlanner(JointPlanner):
    """Finish targets near the next coverage leg; defer distant returns."""
    def __init__(self, robot, **kwargs):
        super().__init__(robot, family='anchors', **kwargs)

    def candidates(self):
        nodes = super().candidates()
        scans = [n for n in nodes if n[0]=='scan']
        if not scans:
            return nodes
        route = open_route(self.robot.position,[n[2] for n in scans])
        next_scan = scans[route[0]]
        p,q = np.asarray(self.robot.position),next_scan[2]
        targets=[]
        for n in nodes:
            if n[0]!='target':continue
            detour = np.linalg.norm(n[2]-p)+np.linalg.norm(n[2]-q)-np.linalg.norm(q-p)
            if detour <= 350:
                targets.append(n)
        return targets + [next_scan]
