"""Privileged-information diagnostic only; NOT an executable contest strategy.

Supply exact source positions at time zero to measure the information penalty
of this routing architecture. Absent-channel coverage is still paid for.
This heuristic diagnostic is neither a lower bound nor a valid online score.
"""
import contextlib,hashlib,io,json,shutil,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from service_routing import ServicePlanner
from legacy_strategy import Track
from benchmark import worlds


def main():
    out=ROOT/'verification/information-diagnostic-v1';out.mkdir(exist_ok=False)
    scene,World,physical=worlds();base=json.loads((ROOT/'configs/base-v3.json').read_text())
    base['initial_baseline']=0
    snap=out/'source_snapshot';snap.mkdir()
    for p in [*list((ROOT/'src').glob('*.py')),Path(__file__),physical]:shutil.copy2(p,snap/p.name)
    rows=[]
    for seed in range(10000,10012):
        targets=scene(seed);world=World(targets,seed)
        world.discovered=set(targets)
        planner=ServicePlanner(world,projection=False,merge_stations=False,cover_trials=6,route_restarts=12,**base)
        for channel,target in targets.items():
            t=Track(channel);t.center=np.array(target[:2]);t.radius=.02
            t.poly=t.center+np.array([[-.01,-.01],[.01,-.01],[.01,.01],[-.01,.01]])
            t.history=[dict(position=t.center.tolist(),measure_result='near')]
            planner.tracks[channel]=t
        with contextlib.redirect_stdout(io.StringIO()):planner.run()
        assert world.cleared==set(targets)
        rows.append(dict(seed=seed,n=len(targets),per_source_s=world.virtual/len(targets),distance_m=world.distance_m,measures=world.measure_count,ledger=world.ledger()))
    result=dict(label='Privileged-information architecture diagnostic; not an online result or a lower bound',rows=rows,
        mean_s=float(np.mean([r['per_source_s'] for r in rows])),parameters=base,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()})
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(result['label'],result['mean_s'])


if __name__=='__main__':main()
