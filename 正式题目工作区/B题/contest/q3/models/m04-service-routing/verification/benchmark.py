"""New development/validation split; no official API calls."""
import argparse,ast,contextlib,hashlib,io,json,platform,shutil,sys,time
from pathlib import Path
from trace_world import traced_world
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from convex_cover import ConvexCoverPlanner
from cost_aware import CostAwarePlanner
from merged_cover import MergedCoverPlanner
from combined_cost_cover import CombinedCostCoverPlanner
from service_routing import ServicePlanner,TransitSearchPlanner
from lookahead import LookaheadPlanner
from cover_milp import MilpPlanner


def worlds():
    p=ROOT.parent/'m01-region-routing/verification/verify.py'
    tree=ast.parse(p.read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ['scene','World']]
    ns={};exec('import math,random\nimport numpy as np\nfrom api_client import BudgetReached',ns)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
    return ns['scene'],traced_world(ns['World']),p


def save(p,data):
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8');temp.replace(p)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--config',type=Path,required=True);ap.add_argument('--start',type=int,default=7000)
    ap.add_argument('--count',type=int,default=20);ap.add_argument('--variants',default='baseline,projection,cost,shared')
    ap.add_argument('--edge',action='store_true');ap.add_argument('--error-mode',default='sin',choices=['sin','plus','minus','checker'])
    ap.add_argument('--keep-actions',action='store_true')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    scene,World,physical=worlds();config=json.loads(args.config.read_text(encoding='utf-8'))
    base=json.loads((ROOT/'configs/base-v3.json').read_text());variants=args.variants.split(',')
    snap=args.output/'source_snapshot';snap.mkdir()
    for p in [*list((ROOT/'src').glob('*.py')),Path(__file__),Path(__file__).with_name('trace_world.py'),physical]:shutil.copy2(p,snap/p.name)
    shutil.copy2(args.config,snap/'config.json');shutil.copy2(ROOT/'configs/base-v3.json',snap/'base-v3.json')
    fixtures={seed:scene(seed,edge=args.edge) for seed in range(args.start,args.start+args.count)}
    save(args.output/'fixtures.json',fixtures)
    rows=[];started=time.time()
    for seed,targets in fixtures.items():
        for name in variants:
            world=World(targets,seed,error_mode=args.error_mode);begin=time.perf_counter();error=None
            try:
                factory=ServicePlanner
                params=dict(base,**config.get(name,{}))
                kind=params.pop('_class',None)
                if kind=='v3':factory=ConvexCoverPlanner
                if kind=='v4':factory=CombinedCostCoverPlanner
                if kind=='search':factory=TransitSearchPlanner
                if kind=='lookahead':factory=LookaheadPlanner
                if kind=='milp':factory=MilpPlanner
                if factory in [ServicePlanner,TransitSearchPlanner,LookaheadPlanner,MilpPlanner]:
                    params={'projection':False,'merge_stations':False,**params}
                with contextlib.redirect_stdout(io.StringIO()):factory(world,**params).run()
            except Exception as exc:error=repr(exc)
            rows.append(dict(seed=seed,variant=name,n=len(targets),cleared=len(world.cleared),
                full=world.cleared==set(targets) and error is None,error=error,
                time_s=world.virtual,per_source_s=world.virtual/len(targets),distance_m=world.distance_m,
                measures=world.measure_count,switches=world.switches,failures=world.clear_failures,
                region_checks=world.region_checks,clear_checks=world.clear_checks,compute_s=time.perf_counter()-begin,ledger=world.ledger()))
            if args.keep_actions:save(args.output/f'{seed}-{name}-actions.json',dict(actions=world.action_trace,decisions=world.decision_trace))
        save(args.output/'results.json',rows)
        print(seed,' '.join(f'{r["variant"]}:{r["per_source_s"]:.1f}{"!" if not r["full"] else ""}' for r in rows[-len(variants):]),flush=True)
    summary={}
    for name in variants:
        group=[r for r in rows if r['variant']==name];full=all(r['full'] for r in group)
        summary[name]=dict(cases=len(group),full=sum(r['full'] for r in group),
            mean_s=float(np.mean([r['per_source_s'] for r in group])) if full else None,
            mean_distance_m=float(np.mean([r['distance_m'] for r in group])),
            mean_measures=float(np.mean([r['measures'] for r in group])),max_compute_s=max(r['compute_s'] for r in group))
    save(args.output/'manifest.json',dict(command=sys.argv,python=platform.python_version(),start=started,end=time.time(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()},summary=summary,
        error_model=args.error_mode,layout='edge' if args.edge else 'uniform area',dirty_worktree=True))
    print(json.dumps(summary,indent=2))
    if any(not r['full'] for r in rows):sys.exit(1)


if __name__=='__main__':main()
