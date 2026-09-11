"""Independent offline world; no official simulator access. Deterministic fixtures.

Ground truth is confined to World and validation; planners see only API results.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import random
import shutil
import sys
import time
import numpy as np

MODEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODEL / 'src'))
from strategy import Planner, Coverage, Track, scan_sites
from api_client import BudgetReached


def scene(seed, edge=False):
    rng = random.Random(seed)
    targets = {}
    count = rng.randint(10, 16)
    for channel in rng.sample(range(1, 21), count):
        angle, radius = rng.uniform(0, 2 * math.pi), 1800 * math.sqrt(rng.random())
        targets[channel] = [radius * math.cos(angle), radius * math.sin(angle), rng.uniform(1000, 1500)]
    if edge:
        # Boundary, origin, nearly collinear and clustered layouts; R=1000.
        count = 10 if seed % 2 else 16
        for i in range(count):
            angle = 2 * math.pi * i / count + .001 * seed
            radius = 1800 if seed % 4 == 0 else (5.001 if seed % 4 == 1 else
                     (1799 if seed % 4 == 2 else 1000))
            if seed % 4 == 2:
                angle = .0001 * i
            targets[i + 1] = [radius * math.cos(angle), radius * math.sin(angle), 1000.]
        targets = {c: targets[c] for c in range(1, count + 1)}
    return targets


class World:
    def __init__(self, targets, seed, error_mode='sin', keep_events=False):
        self.targets, self.seed, self.error_mode = targets, seed, error_mode
        self.position, self.channel = (0., 0.), 1
        self.cleared, self.discovered = set(), set()
        self.virtual = self.distance_m = 0.
        self.measure_count = self.clear_failures = self.scanned_sites = self.switches = 0
        self.events = []
        self.keep_events = keep_events
        self.region_checks = self.clear_checks = 0

    def check_budget(self):
        if self.virtual > 349000:
            raise BudgetReached('offline budget')

    def record(self, event):
        if self.keep_events:
            self.events.append(event)
        if event['kind'] == 'region':
            # Independent geometric membership from oriented polygon edges,
            # not the wedge/intersection implementation used by the planner.
            p = np.asarray(event['vertices'])
            truth = np.asarray(self.targets[event['channel']][:2])
            edges = np.roll(p, -1, axis=0) - p
            delta = truth - p
            cross = edges[:, 0] * delta[:, 1] - edges[:, 1] * delta[:, 0]
            assert np.all(cross >= -1e-5 * np.maximum(1., np.linalg.norm(edges, axis=1))), event
            self.region_checks += 1
        if event['kind'] == 'clear_certificate':
            distance = math.dist(event['point'], self.targets[event['channel']][:2])
            assert distance <= event['worst_distance_m'] + 1e-5
            assert event['worst_distance_m'] <= 19.50001
            self.clear_checks += 1

    def move(self, point):
        distance = math.dist(point, self.position)
        self.virtual += distance / 5
        self.distance_m += distance
        self.position = tuple(point)

    def measure(self, point, channel):
        self.move(point)
        self.measure_count += 1
        switched = int(channel != self.channel)
        self.virtual += 5 + switched
        self.switches += switched
        self.channel = channel
        target = self.targets.get(channel) if channel not in self.cleared else None
        distance = math.dist(point, target[:2]) if target else float('inf')
        if target is None or distance > target[2]:
            return {'measure_result': 'no_signal'}
        self.discovered.add(channel)
        if distance <= 5:
            return {'measure_result': 'near'}
        angle = math.degrees(math.atan2(target[1] - point[1], target[0] - point[0]))
        if self.error_mode == 'sin':
            error = math.sin(point[0] * .017 + point[1] * .031 + channel * 2.7 + self.seed)
        elif self.error_mode == 'plus':
            error = 1.
        elif self.error_mode == 'minus':
            error = -1.
        elif self.error_mode == 'checker':
            error = 1. if (math.floor(point[0] / 10) + math.floor(point[1] / 10) + channel) % 2 else -1.
        else:
            raise ValueError(self.error_mode)
        return {'measure_result': 'direction', 'svd_deg': round((angle + error) % 360, 2) % 360}

    def clear(self, point, channel):
        self.move(point)
        target = self.targets.get(channel) if channel not in self.cleared else None
        success = target is not None and math.dist(point, target[:2]) <= 20
        self.virtual += 5 if success else 3
        if success:
            self.cleared.add(channel)
        else:
            self.clear_failures += 1
        return success


def load_baseline(path):
    spec = importlib.util.spec_from_file_location('baseline_frozen', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def geometry_checks():
    coverage = Coverage()
    for p in scan_sites():
        coverage.add(1, p)
    assert coverage.absent(1), 'Seven anchors must cover all retained squares'
    assert not coverage.absent(2)
    # Missing a perimeter station must not be falsely certified by center alone.
    c = Coverage()
    c.add(1, (0, 0))
    assert not c.absent(1)
    # Q1 counterexample: D < 40 but no disk of radius 20 can cover it.
    t = Track(1)
    t.poly = np.array([[0., 0.], [38., 0.], [19., 19 * math.sqrt(3)]])
    from bearing_geometry import enclosing_circle
    t.center, t.radius, _ = enclosing_circle(t.poly)
    assert t.radius > 20 and t.safe_clear_point((0., 0.)) is None
    # Direct angle residuals around 0/360 with worst-case rounding.
    for reading, truth in [(359.995, 1.), (.005, -1.), (180., 181.005)]:
        t = Track(1)
        t.update((0., 0.), {'measure_result': 'direction', 'svd_deg': reading})
        p = np.array([800 * math.cos(math.radians(truth)), 800 * math.sin(math.radians(truth))])
        edges = np.roll(t.poly, -1, axis=0) - t.poly
        d = p - t.poly
        assert np.all(edges[:, 0] * d[:, 1] - edges[:, 1] * d[:, 0] >= -1e-6)
    return dict(squares=len(coverage.centers), all_seven_certified=True,
                one_station_rejected=True, triangle_radius=t.radius)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, default=30)
    parser.add_argument('--extended', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    snapshot = args.output / 'source_snapshot'
    snapshot.mkdir()
    for path in list((MODEL / 'src').glob('*.py')) + [Path(__file__), args.baseline]:
        shutil.copy2(path, snapshot / path.name)
    baseline = load_baseline(args.baseline)
    rows, fixtures = [], []
    geometry = geometry_checks()
    scenarios = [(seed, 'sin', False) for seed in range(args.seeds)]
    if args.extended:
        scenarios += [(seed, mode, False) for mode in ('plus', 'minus', 'checker') for seed in range(10)]
        scenarios += [(seed, mode, True) for seed in range(8) for mode in ('sin', 'checker')]
    for index, (seed, mode, edge) in enumerate(scenarios):
        targets = scene(seed, edge)
        fixtures.append(dict(seed=seed, error_mode=mode, edge=edge, targets=targets))
        variants = ['baseline', 'improved']
        if args.extended and index < 10:
            variants += ['no_opportunistic', 'channel_order']
        for variant in variants:
            world = World(targets, seed, mode, keep_events=(index == 0 and variant == 'improved'))
            t0 = time.perf_counter()
            error = None
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    if variant == 'baseline':
                        baseline.run_strategy(world)
                        reason = 'seven_sites_exhausted'
                    else:
                        planner = Planner(world, opportunistic=variant != 'no_opportunistic',
                                          nearest_order=variant != 'channel_order')
                        reason = planner.run()
                        # False absence would be a logical failure even if a scene finishes.
                        assert not (set(planner.certificate()['absent_channels']) & set(targets))
            except Exception as exc:
                reason, error = 'error', repr(exc)
            elapsed = time.perf_counter() - t0
            row = dict(index=index, seed=seed, error_mode=mode, edge=edge, variant=variant,
                       target_count=len(targets), cleared_count=len(world.cleared),
                       full_clear=world.cleared == set(targets), virtual_time_s=world.virtual,
                       distance_m=world.distance_m, measures=world.measure_count,
                       clear_failures=world.clear_failures, switches=world.switches,
                       scans=world.scanned_sites, elapsed_s=elapsed,
                       region_checks=world.region_checks, clear_checks=world.clear_checks,
                       stop_reason=reason, error=error)
            rows.append(row)
            if world.events:
                (args.output / 'representative_trace.json').write_text(json.dumps(world.events, indent=2), encoding='utf-8')
            # Persist incrementally, including failures.
            (args.output / 'results.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(f'{index + 1}/{len(scenarios)}: seed={seed}, {mode}, edge={edge}; '
              f'improved={next(r for r in rows if r["index"] == index and r["variant"] == "improved")["virtual_time_s"]:.1f}s', flush=True)
    (args.output / 'fixtures.json').write_text(json.dumps(fixtures, indent=2), encoding='utf-8')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}
    manifest = dict(command=sys.argv, started_epoch=started, ended_epoch=time.time(),
                    python=sys.version, numpy=np.__version__, source_sha256=hashes,
                    data='synthetic local world, not official simulator',
                    dirty_worktree=True, geometry_checks=geometry)
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    failures = [r for r in rows if r['variant'] != 'baseline' and (not r['full_clear'] or r['error'])]
    print(f'OFFLINE ONLY: {len(scenarios)} paired scenarios; new-strategy failures={len(failures)}')
    for r in failures:
        print(r)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
