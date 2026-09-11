"""Reconstruct every physical action and independently certify absent-channel coverage."""
import contextlib,hashlib,io,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from voronoi_coverage import covering_radius
from strategy import Planner,POLICIES
from benchmark import worlds


def main():
    out=ROOT/'verification/replay-and-package-v1';out.mkdir(exist_ok=False)
    coverage_cache={};run_checks=[];actions_checked=0
    for name in ['R018-frozen-audit','R019-frozen-random-checker']:
        run=ROOT/'runs'/name;manifest=json.loads((run/'manifest.json').read_text())
        fixtures=json.loads((run/'fixtures.json').read_text());rows=json.loads((run/'results.json').read_text())
        for row in rows:
            trace=json.loads((run/f"{row['seed']}-{row['variant']}-actions.json").read_text())
            targets={int(c):v for c,v in fixtures[str(row['seed'])].items()}
            point=(0.,0.);channel=1;total=0.;distance=0.;cleared=set();negative={c:set() for c in range(1,21)}
            count=0;switches=0
            for action in trace['actions']:
                q=tuple(action['point']);c=action['channel'];step=math.dist(q,point);point=q
                distance+=step;total+=step/5
                source=targets.get(c) if c not in cleared else None
                d=math.dist(q,source[:2]) if source is not None else float('inf')
                if action['kind']=='measure':
                    count+=1;switches+=int(c!=channel);total+=5+int(c!=channel);channel=c
                    if source is None or d>source[2]:expected={'measure_result':'no_signal'};negative[c].add(q)
                    elif d<=5:expected={'measure_result':'near'}
                    else:
                        angle=math.degrees(math.atan2(source[1]-q[1],source[0]-q[0]))
                        mode=manifest['error_model']
                        error=math.sin(q[0]*.017+q[1]*.031+c*2.7+row['seed']) if mode=='sin' else (1. if (math.floor(q[0]/10)+math.floor(q[1]/10)+c)%2 else -1.)
                        expected={'measure_result':'direction','svd_deg':round((angle+error)%360,2)%360}
                    assert expected==action['response']
                else:
                    success=source is not None and d<=20
                    assert success and action['success'];cleared.add(c);total+=5
                assert abs(total-action['time_s'])<1e-6
                actions_checked+=1
            assert cleared==set(targets) and count==row['measures'] and switches==row['switches']
            assert abs(distance-row['distance_m'])<1e-6 and abs(total-row['time_s'])<1e-6
            certificates=[e for e in trace['decisions'] if e['kind']=='clear_certificate']
            assert len(certificates)==len(targets)
            for e in certificates:
                assert math.dist(e['point'],targets[e['channel']][:2])<=e['worst_distance_m']+1e-5
                assert e['worst_distance_m']<=19.50001
            completion=[e for e in trace['decisions'] if e['kind']=='completion_certificate'][-1]
            if len(cleared)<16:
                assert set(completion['absent_channels'])==set(range(1,21))-set(targets)
                for c in completion['absent_channels']:
                    pts=completion['no_signal_positions'][str(c)]
                    assert all(tuple(p) in negative[c] for p in pts)
                    key=tuple(sorted(set(tuple(p) for p in pts)))
                    if key not in coverage_cache:coverage_cache[key]=covering_radius(key)[0]
                    assert coverage_cache[key]<=1000.-1e-5
        run_checks.append(dict(run=name,executions=len(rows),all_actions_match=True,all_full=True))
    final=ROOT/'runs/R018-frozen-audit';manifest=json.loads((final/'manifest.json').read_text())
    hashes={}
    for p in (ROOT/'src').glob('*.py'):
        assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_sha256'][p.name],p.name
        hashes[p.name]=manifest['source_sha256'][p.name]
    config=json.loads((ROOT/'configs/frozen-v05.json').read_text());base=json.loads((ROOT/'configs/base-v3.json').read_text())
    policy_names={'v3':'baseline_v3','v4':'combined_v4','v5':'service_v5'}
    for name,policy in policy_names.items():assert POLICIES[policy]==dict(base,**config[name])
    fixtures=json.loads((final/'fixtures.json').read_text());rows=json.loads((final/'results.json').read_text());_,World,_=worlds()
    factory=[]
    for seed in [12000,12050]:
        for variant,policy in policy_names.items():
            world=World({int(c):v for c,v in fixtures[str(seed)].items()},seed)
            with contextlib.redirect_stdout(io.StringIO()):Planner(world,policy=policy).run()
            ref=next(r for r in rows if r['seed']==seed and r['variant']==variant)
            assert abs(world.virtual-ref['time_s'])<1e-7 and world.cleared==set(world.targets)
            factory.append(dict(seed=seed,policy=policy,matches_frozen_audit=True))
    result=dict(runs=run_checks,physical_actions_checked=actions_checked,independent_cover_sets=len(coverage_cache),
        largest_absence_covering_radius_m=max(coverage_cache.values()),factory_checks=factory,source_sha256=hashes,
        official_network_calls=False,note='The nearest-site circle coverage checker is independent of the grid-corner completion implementation used by v3/v4/v5.')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':main()
