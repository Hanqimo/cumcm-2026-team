"""No-network delivery and geometry audit, separate from policy tuning."""
import contextlib
import io
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from strategy import Planner,POLICIES
from joint_strategies import exclude_union_hull
from benchmark import world_module


def main():
    scene,World,_=world_module()
    reference=json.loads((ROOT/'runs/R039-final-audit-recovery/results.json').read_text())
    records=[]
    for policy in POLICIES:
        w=World(scene(5100),5100,keep_events=True)
        with contextlib.redirect_stdout(io.StringIO()):Planner(w,policy=policy).run()
        row=next(r for r in reference if r['seed']==5100 and r['variant']==policy)
        assert w.cleared==set(w.targets)
        assert abs(w.virtual-row['time_s'])<1e-7
        assert w.measure_count==row['measures']
        # The real API logger rejects NaN, infinity and non-JSON values.
        json.dumps(w.events,allow_nan=False)
        records.append(dict(policy=policy,per_source_s=w.virtual/len(w.targets),
                            region_checks=w.region_checks,clear_checks=w.clear_checks,
                            log_events=len(w.events),matches_benchmark=True))
    rng=np.random.default_rng(920761)
    tested=0;cases=0
    for _ in range(200):
        size=rng.uniform(100,1600,2);center=rng.uniform(-500,500,2)
        poly=center+np.array([[-size[0],-size[1]],[size[0],-size[1]],size,[-size[0],size[1]]])
        negatives=rng.uniform(-1800,1800,(rng.integers(1,6),2))
        points=rng.uniform(-1,1,(4000,2))*size+center
        # Direct distance classification, independent of edge/circle enumeration.
        feasible=points[np.all(np.linalg.norm(points[:,None,:]-negatives[None,:,:],axis=2)>=999.8+1e-5,axis=1)]
        if not len(feasible):continue
        hull=exclude_union_hull(poly,negatives.tolist())
        edges=np.roll(hull,-1,axis=0)-hull
        delta=feasible[:,None,:]-hull[None,:,:]
        cross=edges[None,:,0]*delta[:,:,1]-edges[None,:,1]*delta[:,:,0]
        assert np.all(cross>=-1e-5*np.maximum(1.,np.linalg.norm(edges,axis=1)))
        tested+=len(feasible);cases+=1
    minimum_spacing=3600*math.sin(math.pi/10)
    movement_lower=1780+9*(minimum_spacing-40)
    report=dict(factory_checks=records,negative_hull_cases=cases,feasible_points_checked=tested,
        ring10_lower_bound=dict(radius_m=1800,clear_radius_m=20,min_pair_spacing_m=minimum_spacing,
        movement_lower_bound_m=movement_lower,time_lower_bound_s=movement_lower/5+50,
        per_source_lower_bound_s=(movement_lower/5+50)/10,
        interpretation='Even with exact positions, and without sensing/search costs; worst-case counterexample, not an average-distribution lower bound.'),
        scope='Finite implementation audits plus documented geometric arguments; no universal completion/runtime theorem.')
    out=ROOT/'verification/integration-audit.json'
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
