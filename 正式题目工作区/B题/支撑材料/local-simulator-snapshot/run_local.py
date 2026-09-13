"""Default Q3/Q4 local simulator. No official HTTP or desktop operations."""
from pathlib import Path
import argparse, contextlib, hashlib, importlib, io, json, platform, shutil, sys, time
import numpy as np
from b_local_simulator import fixture, World, Robot

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(p)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--problem',type=int,choices=[3,4],required=True)
    ap.add_argument('--policy',help='Bundled: v4/v6 for Q3, j500 for Q4; custom policy with --strategy-dir')
    ap.add_argument('--strategy-dir',type=Path,help='New candidate source directory; factory receives only Robot')
    ap.add_argument('--factory',default='strategy:Planner',help='module:callable')
    ap.add_argument('--planner-kwargs',type=Path,help='JSON constructor arguments, replacing the default policy keyword')
    ap.add_argument('--count',type=int,default=50)
    ap.add_argument('--start',type=int,default=2026091300,help='Fresh seed range, distinct from calibration runs')
    ap.add_argument('--errors',choices=['sin','hash_uniform','plus','minus','checker'],default='sin')
    ap.add_argument('--pure-types',action='store_true',help='Q4 alternating K=0/K=N, N=10..16')
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();defaults=read(HERE/'defaults.json');profile=read(HERE/defaults['profile'])
    if a.count<1:ap.error('--count must be positive')
    if a.pure_types and a.problem!=4:ap.error('--pure-types applies only to Q4')
    policy=a.policy or defaults['problem_defaults'][str(a.problem)]
    if a.strategy_dir:
        source=a.strategy_dir.resolve();spec=None
        if not source.is_dir():ap.error('--strategy-dir does not exist')
    else:
        spec=defaults['policies'].get(policy)
        if spec is None or spec['problem']!=a.problem:ap.error('Policy/problem mismatch; use --strategy-dir for a new candidate')
        source=HERE/spec['directory']
        for name,digest in spec['source_sha256'].items():
            if sha(source/name)!=digest:raise RuntimeError(f'Frozen baseline changed: {name}; use a separate candidate directory')
    kwargs=read(a.planner_kwargs) if a.planner_kwargs else {'policy':spec['policy_argument'] if spec else policy}
    if not isinstance(kwargs,dict):ap.error('--planner-kwargs must contain a JSON object')
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    snap=a.output/'simulator_snapshot';snap.mkdir()
    for name in ['b_local_simulator.py','calibrated_profile.json','defaults.json','run_local.py']:
        shutil.copy2(HERE/name,snap/name)
    strategy_snap=a.output/'strategy_snapshot';strategy_snap.mkdir()
    # Freeze the actual candidate before importing; nested packages are retained.
    for p in source.rglob('*'):
        if p.is_file() and p.suffix in ('.py','.json') and p.name!='config.json' and not any(x in ('runs','__pycache__','.git') for x in p.relative_to(source).parts):
            dest=strategy_snap/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    sys.path.insert(0,str(strategy_snap))
    module,name=a.factory.split(':',1)
    factory=getattr(importlib.import_module(module),name)
    rows=[];scenes=[]
    manifest=dict(simulator_id=defaults['simulator_id'],simulator_entry=str(HERE/'b_local_simulator.py'),official=False,problem=a.problem,
        policy=policy,factory=a.factory,planner_kwargs=kwargs,source=str(source),command=sys.argv,python=platform.python_version(),errors=a.errors,
        start=a.start,count=a.count,pure_types=a.pure_types,status='running',
        simulator_sha256={p.name:sha(p) for p in snap.iterdir()},strategy_sha256={p.relative_to(strategy_snap).as_posix():sha(p) for p in strategy_snap.rglob('*') if p.is_file()})
    save(a.output/'manifest.json',manifest)
    print(f"Simulator: {defaults['simulator_id']} | Q{a.problem} | {policy}",flush=True)
    for i in range(a.count):
        n=10+(i//2)%7 if a.pure_types else None;k=(n if i%2 else 0) if a.pure_types else None
        data=fixture(a.start+i,a.problem,profile,n=n,k=k,error_mode=a.errors);scenes.append(data)
        w=World(data);robot=Robot(w);begin=time.perf_counter();error=None
        try:
            with contextlib.redirect_stdout(io.StringIO()):factory(robot,**kwargs).run()
        except Exception as exc:error=repr(exc)
        full=len(w.cleared)==data['n'] and error is None
        row=dict(seed=data['seed'],problem=a.problem,policy=policy,n=data['n'],k=data['directional'],cleared=len(w.cleared),full=full,error=error,
            time_s=w.virtual,per_source_s=w.virtual/data['n'],distance_m=w.distance,measures=w.measures,switches=w.switches,failures=w.failures,compute_s=time.perf_counter()-begin)
        rows.append(row);save(a.output/f'{data["seed"]}-actions.json',dict(actions=w.events,decisions=robot.decisions))
        save(a.output/'results.json',rows);save(a.output/'fixtures.json',scenes)
        print(f"[{i+1}/{a.count}] {row['cleared']}/{data['n']} | {row['per_source_s']:.2f} s/source | {error or 'OK'}",flush=True)
    manifest.update(status='completed',runs=len(rows),full=sum(r['full'] for r in rows),mean_s=float(np.mean([r['per_source_s'] for r in rows])) if all(r['full'] for r in rows) else None)
    save(a.output/'manifest.json',manifest)
    return 0 if all(r['full'] for r in rows) else 1

if __name__=='__main__':sys.exit(main())
