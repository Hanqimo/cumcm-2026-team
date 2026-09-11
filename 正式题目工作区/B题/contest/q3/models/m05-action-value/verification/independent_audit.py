"""Direct physical replay; continuous disk cover checked by a disk union."""
import argparse,json,math
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from shapely import wkt


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',nargs='+',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();assert not args.output.exists();records=[];cache={}
    theta=(np.arange(720)+.5)*2*math.pi/720
    arena=Polygon(1800/np.cos(math.pi/720)*np.column_stack([np.cos(theta),np.sin(theta)]))
    for run in args.runs:
        fixtures=json.loads((run/'fixtures.json').read_text());results=json.loads((run/'results.json').read_text())
        for row in results:
            assert row['full'] and not row['error'],row
            data=json.loads((run/f"{row['seed']}-{row['variant']}-actions.json").read_text())
            targets=fixtures[str(row['seed'])];position=(0,0);channel=1;elapsed=0.;cleared=set();negative={c:[] for c in range(1,21)}
            for a in data['actions']:
                q=a['point'];c=a['channel'];elapsed+=math.dist(position,q)/5;position=q
                target=targets.get(str(c));dist=math.dist(q,target[:2]) if target and c not in cleared else math.inf
                if a['kind']=='clear':
                    success=dist<=20;assert success==a['success']
                    elapsed+=5 if success else 3
                    if success:cleared.add(c)
                else:
                    elapsed+=5+int(channel!=c);channel=c;response=a['response']
                    expected='no_signal' if target is None or dist>target[2] else 'near' if dist<=5 else 'direction'
                    assert response['measure_result']==expected
                    if expected=='no_signal':negative[c].append(q)
                    if expected=='direction':
                        angle=math.degrees(math.atan2(target[1]-q[1],target[0]-q[0]));delta=(response['svd_deg']-angle+180)%360-180
                        assert abs(delta)<=1.00501
                assert abs(elapsed-a['time_s'])<1e-6
            assert cleared==set(map(int,targets)) and abs(elapsed-row['time_s'])<1e-6
            cert=[d for d in data['decisions'] if d['kind']=='completion_certificate'][-1]
            max_hole=0.
            for c in cert['absent_channels']:
                pts=negative[c];key=tuple(map(tuple,pts))
                assert pts
                if key not in cache:
                    # Inscribed 256-sided disks remain within the valid 1000m exclusion.
                    covered=unary_union([Point(q).buffer(999.999,quad_segs=64) for q in pts])
                    cache[key]=arena.difference(covered).area
                max_hole=max(max_hole,cache[key]);assert cache[key]<1e-5
            for d in data['decisions']:
                if d['kind']=='optical_failure_update':
                    truth=targets[str(d['channel'])][:2]
                    assert math.dist(truth,d['point'])>20
                    assert wkt.loads(d['wkt']).distance(Point(truth))<1e-6
            assert len(cleared)==16 or len(cleared)+len(cert['absent_channels'])==20
            records.append(dict(seed=row['seed'],variant=row['variant'],actions=len(data['actions']),max_uncovered_area_m2=max_hole))
    result=dict(passed=True,executions=len(records),actions=sum(r['actions'] for r in records),independent_cover_unions=len(cache),records=records)
    args.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__=='__main__':main()
