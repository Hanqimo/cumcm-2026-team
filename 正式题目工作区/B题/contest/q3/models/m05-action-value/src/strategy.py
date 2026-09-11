"""Frozen optical-action candidate and previous v5 control."""
import json
from pathlib import Path
from service_routing import ServicePlanner
from action_value import ActionValuePlanner
VERSION='p3-action-value-v6-research'
POLICIES=json.loads(Path(__file__).with_name('policies.json').read_text(encoding='utf-8'))
def Planner(robot,*,policy='v6'):
    params=POLICIES[policy].copy();kind=params.pop('_class',None)
    return (ActionValuePlanner if kind=='action' else ServicePlanner)(robot,**params)
