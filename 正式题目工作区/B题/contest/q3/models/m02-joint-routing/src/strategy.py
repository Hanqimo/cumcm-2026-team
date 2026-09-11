"""Frozen, selectable P3 research candidates; 200 s/source is not achieved."""
import json
from pathlib import Path
from joint_strategies import JointPlanner
from convex_cover import ConvexCoverPlanner

VERSION='p3-joint-routing-v3-research'
POLICIES=json.loads((Path(__file__).with_name('policies.json')).read_text(encoding='utf-8'))


def Planner(robot,*,policy='combined_cover'):
    if policy not in POLICIES:raise ValueError(f'Unknown policy: {policy}')
    config=POLICIES[policy].copy()
    kind=config.pop('_class','joint')
    factory=ConvexCoverPlanner if kind=='convex_cover' else JointPlanner
    return factory(robot,**config)
