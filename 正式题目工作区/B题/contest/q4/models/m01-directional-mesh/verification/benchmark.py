"""Independent P4 physical simulator; fixtures and every action are retained."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
import time
import numpy as np
from shapely.geometry import Polygon, Point

MODEL = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODEL/'src'))
from strategy import Planner, POLICIES


def fixture(seed, stress=None):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(10,17))
    channels = rng.choice(np.arange(1,21),n,replace=False)
    angles = rng.uniform(0,2*math.pi,n)
    radii = 1800*np.sqrt(rng.random(n))
    flags = rng.random(n)<.5
    flags[0],flags[1] = True,False
    emit = rng.uniform(0,360,n)
    reception = rng.uniform(1000,1500,n)
    if stress=='outward_boundary':
        radii[:]=1800.;flags[:]=True;flags[-1]=False
        emit=np.degrees(angles);reception[:]=1000.
    if stress=='tangent_boundary':
        radii[:]=1799.99;flags[:]=True;flags[-1]=False
        emit=np.degrees(angles)+90;reception[:]=1000.
    if stress=='near_cluster':
        radii[:]=rng.uniform(.1,40,n);flags[:]=True;flags[-1]=False
        reception[:]=1000.
    sources=[dict(channel=int(c),position=[float(r*math.cos(a)),float(r*math.sin(a))],
                  radius_m=float(R),direction_deg=float(e%360) if flag else None)
             for c,r,a,R,e,flag in zip(channels,radii,angles,reception,emit,flags)]
    return dict(seed=seed,sources=sources,stress=stress)


def error_at(point,channel,seed,mode):
    x,y=point
    if mode=='plus':return 1.
    if mode=='minus':return -1.
    if mode=='checker':return 1. if (math.floor(x/37)+math.floor(y/41)+channel)%2 else -1.
    return math.sin(.013*x+.019*y+channel*1.7+seed*.31)


class World:
    def __init__(self, data, error_mode='smooth'):
        self.sources={s['channel']:s for s in data['sources']}
        self.seed=data['seed'];self.error_mode=error_mode
        self.position=(0.,0.);self.channel=1;self.virtual=0.
        self.cleared=set();self.discovered=set()
        self.measure_count=self.clear_failures=self.scanned_sites=self.switches=0
        self.distance_m=0.;self.events=[];self.actions=[];self.max_region_excess=0.
        self.last_clear_time=0.;self.certified_failures=0

    def check_budget(self):
        if len(self.actions)>=10000 or self.virtual>349000:
            raise RuntimeError('Offline action/virtual budget')

    def record(self, event):
        self.events.append(event)
        if event['kind']=='region':
            truth=np.array(self.sources[event['channel']]['position'])
            p=Polygon(event['vertices'])
            excess=p.distance(Point(truth))
            self.max_region_excess=max(self.max_region_excess,float(excess))
            if excess>1e-5:raise AssertionError('True source excluded from region')
        if event['kind']=='clear_certificate':
            truth=self.sources[event['channel']]['position']
            if math.dist(truth,event['point'])>event['worst_distance_m']+1e-5:
                raise AssertionError('Incorrect bound')

    def move(self,point):
        d=math.dist(self.position,point);self.distance_m+=d;self.virtual+=d/5
        self.position=tuple(point)

    def measure(self,point,channel):
        self.check_budget();before=self.virtual
        self.move(point);self.switches+=int(channel!=self.channel)
        self.virtual+=5+int(channel!=self.channel);self.channel=channel;self.measure_count+=1
        s=self.sources.get(channel);result={'measure_result':'no_signal'}
        if s and channel not in self.cleared:
            dx,dy=point[0]-s['position'][0],point[1]-s['position'][1]
            d=math.hypot(dx,dy);a=s['direction_deg']
            visible=a is None or dx*math.cos(math.radians(a))+dy*math.sin(math.radians(a))>=-1e-10
            if d<=s['radius_m']+1e-9 and visible:
                self.discovered.add(channel)
                if d<=5+1e-9:result={'measure_result':'near'}
                else:
                    bearing=math.degrees(math.atan2(-dy,-dx))%360
                    value=round((bearing+error_at(point,channel,self.seed,self.error_mode))%360,2)%360
                    result={'measure_result':'direction','svd_deg':value}
        self.actions.append(dict(kind='measure',point=list(point),channel=channel,response=result,
                                 virtual_time_s=self.virtual,delta_s=self.virtual-before))
        return result

    def clear(self,point,channel):
        self.check_budget();before=self.virtual;self.move(point)
        s=self.sources.get(channel)
        ok=bool(s and channel not in self.cleared and math.dist(point,s['position'])<=20+1e-9)
        self.virtual+=5 if ok else 3
        if ok:self.cleared.add(channel);self.last_clear_time=self.virtual
        else:self.clear_failures+=1
        self.actions.append(dict(kind='clear',point=list(point),channel=channel,success=ok,
                                 virtual_time_s=self.virtual,delta_s=self.virtual-before))
        return ok


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--start',type=int,default=20000);p.add_argument('--count',type=int,default=4)
    p.add_argument('--policies',default='mesh_chase_baseline,directional_v1')
    p.add_argument('--error',choices=['smooth','plus','minus','checker'],default='smooth')
    p.add_argument('--stress',choices=['outward_boundary','tangent_boundary','near_cluster'])
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    snap=out/'source_snapshot';snap.mkdir();hashes={}
    for f in list((MODEL/'src').glob('*.py'))+[MODEL/'src/policies.json',Path(__file__)]:
        shutil.copy2(f,snap/f.name);hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
    manifest=dict(started_at=dt.datetime.now(dt.timezone.utc).isoformat(),command=sys.argv,
                  python=sys.version,numpy=np.__version__,platform=platform.platform(),
                  sources_sha256=hashes,policies=POLICIES,official_simulator=False,
                  error_mode=args.error,fixtures='uniform disk/range/orientation unless labelled stress')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for seed in range(args.start,args.start+args.count):
        data=fixture(seed,args.stress)
        (out/f'fixture-{seed}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        for policy in args.policies.split(','):
            world=World(data,args.error);planner=Planner(world,policy);t0=time.perf_counter();error=None
            try:planner.run()
            except Exception as exc:error=f'{type(exc).__name__}: {exc}'
            row=dict(seed=seed,policy=policy,actual_count=len(data['sources']),cleared=len(world.cleared),
                     all_cleared=len(world.cleared)==len(data['sources']),error=error,
                     virtual_time_s=world.virtual,average_s=world.virtual/len(data['sources']),
                     distance_m=world.distance_m,measures=world.measure_count,switches=world.switches,
                     failed_optical_attempts=world.clear_failures,tail_s=world.virtual-world.last_clear_time,
                     wall_s=time.perf_counter()-t0,max_region_excess_m=world.max_region_excess,
                     completion=planner.certificate())
            record=dict(result=row,actions=world.actions,events=world.events)
            (out/f'{seed}-{policy}.json').write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
            rows.append(row)
            (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(f'{seed} {policy}: {row["cleared"]}/{row["actual_count"]} {row["average_s"]:.2f} s/source {row["wall_s"]:.2f}s CPU {error or ""}',flush=True)
    manifest['completed_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    manifest['executions']=len(rows)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
