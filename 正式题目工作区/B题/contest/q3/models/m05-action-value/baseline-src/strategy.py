"""Frozen v3/v4 controls and the v5 service-routing research candidate."""
import json
from pathlib import Path
from convex_cover import ConvexCoverPlanner
from combined_cost_cover import CombinedCostCoverPlanner
from service_routing import ServicePlanner

VERSION = 'p3-service-routing-v5-research'
POLICIES = json.loads(Path(__file__).with_name('policies.json').read_text(encoding='utf-8'))


def Planner(robot, *, policy='service_v5'):
    if policy not in POLICIES:
        raise ValueError(f'Unknown policy: {policy}')
    config = POLICIES[policy].copy()
    kind = config.pop('_class',None)
    factory = ConvexCoverPlanner if kind=='v3' else CombinedCostCoverPlanner if kind=='v4' else ServicePlanner
    return factory(robot, **config)
