"""Deterministic covering grid and multistart refinement for general first observations.
Internal q uses the first measured bearing as +x; every output also contains O-centered q.
No origin result is used to initialize the new origin search.
"""
from pathlib import Path
import csv,json,subprocess,time,math,sys,argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
SOLVER=str(ROOT/'solver')
CASES=[(0,0),(900,0),(900,90),(1700,0),(1700,90),(1780,0),(2500,180),(2500,150)]

def minimize(fun,x0,step=20,xatol=.05,fatol=1e-6,maxiter=140):
 x=np.array(x0,dtype=float);s=np.array([x,x+[step,0],x+[0,step]]);v=np.array([fun(x) for x in s]);success=False
 for it in range(maxiter):
  ids=np.argsort(v);s=s[ids];v=v[ids]
  if np.max(np.abs(s[1:]-s[0]))<=xatol and np.ptp(v)<=fatol:success=True;break
  c=s[:2].mean(0);xr=2*c-s[2];fr=fun(xr)
  if fr<v[0]:
   xe=c+2*(xr-c);fe=fun(xe);s[2],v[2]=(xe,fe) if fe<fr else (xr,fr)
  elif fr<v[1]:s[2],v[2]=xr,fr
  else:
   outside=fr<v[2];xc=c+.5*((xr if outside else s[2])-c);fc=fun(xc)
   if fc<(fr if outside else v[2]):s[2],v[2]=xc,fc
   else:s[1:]=s[0]+.5*(s[1:]-s[0]);v[1:]=[fun(z) for z in s[1:]]
 j=int(np.argmin(v));return s[j],{'success':success,'iterations':it+1,'simplex_diameter_m':float(np.max(np.linalg.norm(s-s[j],axis=1))),'simplex_value_spread':float(np.ptp(v))}

def run(a,b):
 start=time.monotonic();case=f'a{a:g}_b{b:g}';out=ROOT/'results'/case;out.mkdir(exist_ok=True)
 prefix=[SOLVER,str(a),str(b)]
 info=json.loads(subprocess.check_output(prefix+['info'],text=True));(out/'initial_geometry.json').write_text(json.dumps(info,indent=2))
 cache={};history=[]
 def ev(q,lev):
  x,y=map(float,q);key=(x,y,lev)
  # The finite enclosing disk is a safe superset of the model's candidate domain.
  gx=a+math.cos(math.radians(b))*x-math.sin(math.radians(b))*y;gy=math.sin(math.radians(b))*x+math.cos(math.radians(b))*y
  if math.hypot(x,y)<1e-10 or math.hypot(gx,gy)>3300+1e-7:return {'J':1e20,'E_radius_loss':1e20,'x':x,'y':y}
  if key not in cache:
   r={k:float(v) for k,v in next(csv.DictReader(subprocess.check_output(prefix+['eval',str(x),str(y),str(lev)],text=True).splitlines())).items()};r['level']=lev
   if not all(math.isfinite(v) for v in r.values()):raise RuntimeError('Nonfinite evaluator output')
   cache[key]=r;history.append(r)
  return cache[key]
 def batch(name,points,lev):
  ip=out/f'{name}_input.csv';op=out/f'{name}.csv'
  with ip.open('w')as f:w=csv.writer(f);w.writerow(['x','y']);w.writerows(points)
  subprocess.run(prefix+['batch',str(ip),str(op),str(lev)],check=True,stderr=subprocess.DEVNULL)
  records=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(op.open())]
  for r in records:r['level']=lev;cache[r['x'],r['y'],lev]=r;history.append(r)
  return records
 # A nonnegative-objective certificate: all initial source locations within 20 m of q.
 if info['rho1']<=20:
  v=ev(info['center'],5);assert v['J']==0 and v['E_radius_loss']==0
  best={k:dict(v,optimizer={'success':True,'reason':'rho(K1)<=20, zero objective is globally minimal'}) for k in ['area','radius']}
  allrows=[];proof=True
 else:
  p=np.asarray(info['points']);lo=p.min(0)-1501;hi=p.max(0)+1501
  # Arc bulges relative to listed endpoints are <1 m for the first +/-1 degree sector.
  gx=np.arange(math.floor(lo[0]/100)*100,hi[0]+100,100);gy=np.arange(math.floor(lo[1]/100)*100,hi[1]+100,100)
  allrows=batch('global100',[(float(x),float(y)) for x in gx for y in gy],2)
  xmin=max(5.,float(p[:,0].min())-1);xmax=min(1500.,float(p[:,0].max())+1);span=xmax-xmin;dx=max(1.,min(25.,span/50))
  band=[(float(x),float(y)) for x in np.arange(xmin,xmax+dx*.5,dx) for y in [-50,-30,-20,-10,-5,-2,0,2,5,10,20,30,50]]
  allrows+=batch('strong_optical_band',band,2)
  # Cover the source-sized central design region with a finer 2D mesh as well.
  step=max(2.,min(25.,span/20));xx=np.arange(xmin-.25*span,xmax+.25*span+step,step);yy=np.arange(-.8*span,.8*span+step,step)
  allrows+=batch('central_grid',[(float(x),float(y)) for x in xx for y in yy],2)
  print(case,'grids done',len(allrows),'seconds',round(time.monotonic()-start,2),flush=True)
  best={};proof=False
  for obj,col in [('area','J'),('radius','E_radius_loss')]:
   seeds=[]
   for r in sorted(allrows,key=lambda r:r[col]):
    q=np.array([r['x'],r['y']])
    if all(np.linalg.norm(q-z)>max(5.,span*.075) for z in seeds):seeds.append(q)
    if len(seeds)==6:break
   starts=[]
   for q in seeds:
    z,diag=minimize(lambda q:ev(q,3)[col],q,step=min(20.,max(1.,span*.03)),xatol=.03,fatol=1e-7,maxiter=130)
    starts.append(dict(ev(z,3),optimizer=diag,seed=q.tolist()))
   (out/f'{obj}_multistart.json').write_text(json.dumps(starts,indent=2))
   # Refine two distinct basins at high precision to avoid a coarse-integration ranking artefact.
   refined=[];selected=[]
   for r in sorted(starts,key=lambda r:r[col]):
    q=np.array([r['x'],r['y']])
    if any(np.linalg.norm(q-z)<.2 for z in selected):continue
    selected.append(q)
    z,diag=minimize(lambda q:ev(q,5)[col],q,step=min(3.,max(.1,span*.003)),xatol=.005,fatol=1e-9,maxiter=120)
    refined.append(dict(ev(z,5),optimizer=diag))
    if len(selected)>=2:break
   best[obj]=min(refined,key=lambda r:r[col]);(out/f'{obj}_refined.json').write_text(json.dumps(refined,indent=2))
   print(case,obj,best[obj],flush=True)
  # Neighbor checks at three physical scales, independent of the final simplex orientation.
  for obj,col in [('area','J'),('radius','E_radius_loss')]:
   r=best[obj];checks=[]
   for h in [.01,.1,1.]:
    for ang in np.arange(8)*math.pi/4:checks.append(ev((r['x']+h*math.cos(ang),r['y']+h*math.sin(ang)),5))
   (out/f'{obj}_neighbors.json').write_text(json.dumps(checks,indent=2))
  # Near-optimal listed points are sampled, not a certificate for the entire cell.
  for obj,col in [('area','J'),('radius','E_radius_loss')]:
   r=best[obj];h=max(.5,min(5.,span/100));points=[(r['x']+i*h,r['y']+j*h) for i in range(-10,11) for j in range(-10,11)]
   near=batch(f'{obj}_near_grid',points,3);near=[z for z in near if z[col]<=1.01*r[col]]
   (out/f'{obj}_near_1pct.json').write_text(json.dumps({'step_m':h,'points':near,'note':'sampled candidate set; not a certified continuous 1% region'},indent=2))
 result={'a_m':a,'beta_deg':b,'initial_geometry':info,'best':best,'elapsed_seconds':time.monotonic()-start,'evaluation_count':len(history),'global_optimality_proven':proof,'status':'zero-loss global minimum' if proof else 'best candidates from covering grids and multistart refinement; no continuous-global certificate','coordinates':'x,y relative to S1 with measured bearing as +x; x_global,y_global use O origin and S1=(a,0)'}
 (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 with (out/'evaluations.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(history[0]));w.writeheader();w.writerows(history)
 print('DONE',case,'seconds',round(result['elapsed_seconds'],2),flush=True)
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--a',type=float);parser.add_argument('--beta',type=float);args=parser.parse_args()
 cases=[(args.a,args.beta)] if args.a is not None else CASES
 (ROOT/'inputs/scenarios.json').write_text(json.dumps({'cases':cases,'case_selection':'representative internal, boundary, external and origin scenarios; not an exhaustive parameter sweep'},indent=2))
 for a,b in cases:run(a,b)
if __name__=='__main__':main()
