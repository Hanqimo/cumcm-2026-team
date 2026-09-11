"""Replay physical costs and check directional certificates by a second geometry.

Planner uses triangle cross products and packed corner masks. Auditor uses a
convex-hull halfspace representation of all eligible actual negative stations,
plus direct distances and a polygon-union check of the arena partition.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from shapely.ops import unary_union


def audit_record(path):
    data=json.loads(path.read_text(encoding='utf-8'));row=data['result'];cert=row['completion']
    assert row['all_cleared'] and not row['error'] and cert['complete'],path
    position=np.zeros(2);channel=1;elapsed=0.;worst_time=0.;negatives={c:[] for c in range(1,21)}
    cleared=set()
    for a in data['actions']:
        elapsed+=math.dist(position,a['point'])/5;position=a['point']
        if a['kind']=='measure':
            elapsed+=5+int(channel!=a['channel']);channel=a['channel']
            if a['response']['measure_result']=='no_signal':negatives[channel].append(position)
        else:
            elapsed+=5 if a['success'] else 3
            if a['success']:cleared.add(a['channel'])
        worst_time=max(worst_time,abs(elapsed-a['virtual_time_s']))
    assert worst_time<1e-6
    assert cleared==set(cert['cleared_channels'])
    checked=0;max_excess=0.;uncovered_area=0.
    if 'coverage_cells' in cert:
        cells=[np.array(c) for c in cert['coverage_cells']]
        # Circumscribed 360-gon; its edge distance from origin is exactly 1800.
        theta=(np.arange(360)+.5)*2*math.pi/360
        arena=Polygon(1800/np.cos(math.pi/360)*np.column_stack([np.cos(theta),np.sin(theta)]))
        uncovered_area=arena.difference(unary_union([Polygon(c) for c in cells])).area
        assert uncovered_area<1e-5,uncovered_area
        for c in cert['excluded_channels']:
            points=np.array(negatives[c]);assert len(points)>=3
            for cell in cells:
                eligible=np.max(np.linalg.norm(points[:,None,:]-cell[None,:,:],axis=2),axis=1)<=999.991
                assert sum(eligible)>=3
                hull=ConvexHull(points[eligible]);violation=float(np.max(cell@hull.equations[:,:2].T+hull.equations[:,2]))
                max_excess=max(max_excess,violation);assert violation<1e-6,(c,violation)
                checked+=1
    assert set(cert['observed_but_uncleared'])==set()
    assert len(cleared)==16 or len(cleared)+len(cert['excluded_channels'])==20
    return dict(file=str(path),actions=len(data['actions']),checked_cells=checked,
                max_cost_difference_s=worst_time,max_hull_violation_m=max_excess,
                uncovered_partition_area_m2=uncovered_area)


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',nargs='+',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    records=[]
    for run in args.runs:
        for path in sorted(run.glob('*-polar22.json')):records.append(audit_record(path))
    assert records
    result=dict(passed=True,records=records,executions=len(records),actions=sum(r['actions'] for r in records),
                cell_checks=sum(r['checked_cells'] for r in records),method=__doc__)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__=='__main__':main()
