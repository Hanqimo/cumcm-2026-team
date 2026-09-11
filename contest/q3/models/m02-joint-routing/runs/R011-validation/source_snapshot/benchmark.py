"""Paired synthetic benchmark. Never calls official APIs."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np

MODEL = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODEL/'src'))
from legacy_strategy import Planner as Baseline
from joint_strategies import JointPlanner, SweepPlanner, SectorPlanner, OrderedPlanner


def world_module():
    # Freeze/extract only the independent scene and physical world definitions.
    source=MODEL.parent/'m01-region-routing/verification/verify.py'
    text=source.read_text(encoding='utf-8')
    tree=ast.parse(text)
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('scene','World')]
    ns={}
    exec('import math,random\nimport numpy as np\nfrom api_client import BudgetReached',ns)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
    return ns['scene'],ns['World'],source


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--start',type=int,default=200)
    ap.add_argument('--count',type=int,default=20)
    ap.add_argument('--variants',default='baseline,joint,anchors,triangulate,sweep')
    ap.add_argument('--config',type=Path)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    scene,World,source=world_module()
    config=json.loads(args.config.read_text()) if args.config else {}
    specs={
        'baseline':(Baseline,{}),
        'joint':(JointPlanner,{}),
        'anchors':(JointPlanner,{'family':'anchors'}),
        'triangulate':(JointPlanner,{'initial_baseline':250.}),
        'sweep':(SweepPlanner,{})}
    for name,params in config.items():
        params=params.copy();kind=params.pop('_class','joint')
        specs[name]=({'sector':SectorPlanner,'ordered':OrderedPlanner}.get(kind,JointPlanner),params)
    variants=args.variants.split(',')
    snap=args.output/'source_snapshot';snap.mkdir()
    for p in list((MODEL/'src').glob('*.py'))+[Path(__file__),source]:shutil.copy2(p,snap/p.name)
    if args.config:shutil.copy2(args.config,snap/'config.json')
    rows=[];started=time.time()
    for seed in range(args.start,args.start+args.count):
        targets=scene(seed)
        for name in variants:
            w=World(targets,seed);factory,kw=specs[name]
            begin=time.perf_counter();error=None;reason=None
            try:
                planner=factory(w,**kw)
                with contextlib.redirect_stdout(io.StringIO()):reason=planner.run()
            except Exception as exc:error=repr(exc)
            rows.append(dict(seed=seed,variant=name,n=len(targets),cleared=len(w.cleared),
                full_clear=w.cleared==set(targets),error=error,time_s=w.virtual,
                per_source_s=w.virtual/len(targets),distance_m=w.distance_m,measures=w.measure_count,
                failures=w.clear_failures,scans=w.scanned_sites,elapsed_s=time.perf_counter()-begin,
                stop_reason=reason,region_checks=w.region_checks))
        (args.output/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(seed,' '.join(f'{r["variant"]}:{r["per_source_s"]:.1f}{"!" if r["error"] else ""}' for r in rows[-len(variants):]),flush=True)
    report={}
    for name in variants:
        group=[r for r in rows if r['variant']==name]
        report[name]=dict(cases=len(group),full=sum(r['full_clear'] and not r['error'] for r in group),
                         mean_per_source_s=float(np.mean([r['per_source_s'] for r in group])),
                         median_per_source_s=float(np.median([r['per_source_s'] for r in group])),
                         mean_distance_m=float(np.mean([r['distance_m'] for r in group])),
                         mean_measures=float(np.mean([r['measures'] for r in group])),
                         max_elapsed_s=max(r['elapsed_s'] for r in group))
    manifest=dict(command=sys.argv,started_epoch=started,ended_epoch=time.time(),
                  data='synthetic uniform disk, fixed bounded spatial sine errors',
                  source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()},
                  dirty_worktree=True,summary=report)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
