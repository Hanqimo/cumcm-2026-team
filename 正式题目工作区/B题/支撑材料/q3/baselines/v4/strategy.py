"""Frozen v4 factory. Research candidate; not an official 200 s/source result."""
import json
from pathlib import Path
from convex_cover import ConvexCoverPlanner
from cost_aware import CostAwarePlanner
from merged_cover import MergedCoverPlanner
from combined_cost_cover import CombinedCostCoverPlanner

VERSION = 'p3-cost-aware-v4-research'
POLICIES = json.loads(Path(__file__).with_name('policies.json').read_text(encoding='utf-8'))


def Planner(robot, *, policy='combined_v4'):
    if policy not in POLICIES:
        raise ValueError(f'Unknown policy: {policy}')
    config = POLICIES[policy].copy()
    kind = config.pop('_class')
    factory = {'convex_cover': ConvexCoverPlanner, 'cost': CostAwarePlanner,
               'merge': MergedCoverPlanner, 'combined': CombinedCostCoverPlanner}[kind]
    return factory(robot, **config)
