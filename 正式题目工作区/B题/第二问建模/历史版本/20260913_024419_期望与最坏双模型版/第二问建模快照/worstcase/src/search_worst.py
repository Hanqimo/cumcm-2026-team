"""Reproducible broad-domain search; angular certificates are computed separately."""
import csv, json, subprocess, sys, time, importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/R001'
SOLVER=ROOT/'worst_solver'
spec=importlib.util.spec_from_file_location('baseline_search',ROOT.parent/'src/search.py')
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)

def batch(name,points,n=6):
    src=RUN/(name+'_input.csv');dest=RUN/(name+'.csv')
    with src.open('w') as f:
        w=csv.writer(f);w.writerow(['x','y']);w.writerows(points)
    subprocess.run([str(SOLVER),'batch',str(src),str(dest),str(n)],check=True,stderr=subprocess.DEVNULL)
    rs=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(dest.open())]
    print(name,len(rs),'best',min(rs,key=lambda r:r['worst_lower']),flush=True)
    return rs

def main():
    start=time.time();RUN.mkdir(parents=True,exist_ok=True)
    grid=batch('global50',[(x,y) for x in range(-1500,3001,50) for y in range(0,1551,50)])
    band=batch('near_sector',[(x,y) for x in range(5,1501,25) for y in [0,1,2,5,10,15,20,25,30,40,50]])
    seeds=[]
    for r in sorted(grid+band,key=lambda r:r['worst_lower']):
        p=np.array([r['x'],r['y']])
        if all(np.linalg.norm(p-s)>100 for s in seeds):seeds.append(p)
        if len(seeds)==14:break
    history=[];cache={}
    def at(q,n=12):
        q=(float(q[0]),abs(float(q[1])));key=(*q,n)
        if key not in cache:
            r=next(csv.DictReader(subprocess.check_output([str(SOLVER),'eval',*map(str,q),str(n)],text=True).splitlines()))
            r={k:float(v) for k,v in r.items()};r['angle_samples_per_interval']=n;cache[key]=r;history.append(r)
        return cache[key]
    optimized=[]
    for i,p in enumerate(seeds):
        res=baseline.minimize(lambda q:at(q)['worst_lower'],p,options={'maxiter':220,'xatol':.005,'fatol':1e-8})
        r=dict(at(res.x),seed=p.tolist(),success=bool(res.success),nit=int(res.nit));optimized.append(r)
        print('seed',i,r,flush=True)
        (RUN/'multistart.json').write_text(json.dumps(optimized,indent=2))
    best=min(optimized,key=lambda r:r['worst_lower'])
    res=baseline.minimize(lambda q:at(q,32)['worst_lower'],[best['x'],best['y']],options={'maxiter':240,'xatol':.00005,'fatol':2e-10})
    best=dict(at(res.x,32),success=bool(res.success),nit=int(res.nit))
    (RUN/'best_search.json').write_text(json.dumps(best,indent=2))
    with (RUN/'local_evaluations.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
    report={'best':best,'elapsed_seconds':time.time()-start,'global_step_m':50,'global_points':len(grid),'near_sector_points':len(band),'multistarts':len(seeds),'global_optimality_proven':False,'angular_suprema_certified_in_this_search':False}
    (RUN/'search_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
