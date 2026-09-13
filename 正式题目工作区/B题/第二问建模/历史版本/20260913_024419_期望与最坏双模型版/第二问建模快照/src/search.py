"""Bounded global grid + independent multistart local searches for two objectives."""
import csv,json,subprocess,time,platform,hashlib,sys
from pathlib import Path
import numpy as np
from types import SimpleNamespace

def minimize(fun, x0, method=None, options=None):
 opts=options or {};x=np.array(x0,dtype=float);simplex=np.array([x,x+[20,0],x+[0,20]]);vals=np.array([fun(v) for v in simplex]);success=False
 for it in range(opts.get("maxiter",150)):
  ids=np.argsort(vals);simplex=simplex[ids];vals=vals[ids]
  if np.max(np.abs(simplex[1:]-simplex[0]))<=opts.get("xatol",.01) and max(vals)-min(vals)<=opts.get("fatol",1e-8):success=True;break
  center=simplex[:2].mean(axis=0);xr=2*center-simplex[2];fr=fun(xr)
  if fr<vals[0]:
   xe=center+2*(xr-center);fe=fun(xe);simplex[2],vals[2]=(xe,fe) if fe<fr else (xr,fr)
  elif fr<vals[1]:simplex[2],vals[2]=xr,fr
  else:
   outside=fr<vals[2];xc=center+.5*((xr if outside else simplex[2])-center);fc=fun(xc)
   if fc<(fr if outside else vals[2]):simplex[2],vals[2]=xc,fc
   else:
    simplex[1:]=simplex[0]+.5*(simplex[1:]-simplex[0]);vals[1:]=[fun(v) for v in simplex[1:]]
 ids=np.argsort(vals);return SimpleNamespace(x=simplex[ids[0]],success=success,nit=it+1)
ROOT=Path(__file__).resolve().parents[1]
SOLVER=str(ROOT/'solver')
def rows(path):return list(csv.DictReader(path.open()))
def batch(name,points,level):
 inp=ROOT/'results'/f'{name}_input.csv';out=ROOT/'results'/f'{name}.csv'
 with inp.open('w')as f:
  w=csv.writer(f);w.writerow(['x','y']);w.writerows(points)
 subprocess.run([SOLVER,'batch',str(inp),str(out),str(level)],check=True,stderr=subprocess.DEVNULL)
 a=rows(out);print(name,len(a),'area',min(a,key=lambda r:float(r['J'])),'radius',min(a,key=lambda r:float(r['E_radius_loss'])),flush=True);return a

def main():
 start=time.time();history=[];cache={}
 globalrows=batch('global50',[(x,y) for x in range(-1500,3001,50) for y in range(0,1551,50)],2)
 band=batch('strong_band',[(x,y) for x in range(5,1501,25) for y in [0,2,5,10,15,20,25,30,40,50]],3)
 def evaluate(q,lev):
  q=(float(q[0]),abs(float(q[1])))
  key=(*q,lev)
  if key not in cache:
   result=next(csv.DictReader(subprocess.check_output([SOLVER,'eval',*map(str,q),str(lev)],text=True).splitlines()))
   r={k:float(v) for k,v in result.items()};r['level']=lev;cache[key]=r;history.append(r)
  return cache[key]
 bests={}
 for objective,column in [('area','J'),('radius','E_radius_loss')]:
  seeds=[]
  for r in sorted(globalrows+band,key=lambda r:float(r[column])):
   q=np.array([float(r['x']),float(r['y'])])
   if all(np.linalg.norm(q-s)>100 for s in seeds):seeds.append(q)
   if len(seeds)==8:break
  optimized=[]
  for i,q in enumerate(seeds):
   res=minimize(lambda q:evaluate(q,3)[column],q,method='Nelder-Mead',options={'maxiter':150,'xatol':.1,'fatol':1e-5})
   r=evaluate(res.x,3);r=dict(r,success=bool(res.success),nit=int(res.nit),seed=q.tolist());optimized.append(r)
   print(objective,'seed',i,'->',r,flush=True)
  top=min(optimized,key=lambda r:r[column]);q=[top['x'],top['y']]
  # High precision deterministic local refinement; external convergence study follows.
  res=minimize(lambda q:evaluate(q,5)[column],q,method='Nelder-Mead',options={'maxiter':150,'xatol':.005,'fatol':1e-8})
  best=dict(evaluate(res.x,5),success=bool(res.success),nit=int(res.nit));bests[objective]=best
  (ROOT/'results'/objective/'best.json').write_text(json.dumps(best,indent=2))
  (ROOT/'results'/objective/'multistart.json').write_text(json.dumps(optimized,indent=2))
  print('FINAL',objective,best,flush=True)
 with (ROOT/'results/local_evaluations.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
 (ROOT/'results/search_summary.json').write_text(json.dumps({'best':bests,'elapsed_seconds':time.time()-start,'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),'global_step_m':50,'domain_box':[-1500,3000,0,1550],'reflection_symmetry':True,'global_optimality_proven':False},indent=2))
if __name__=='__main__':main()
