"""覆盖网格、多起点 Nelder-Mead、精度递增与按权重输出候选位置。"""
from pathlib import Path
import csv,json,math,subprocess,time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
from .nelder_mead import minimize
from .api import binary, initial_geometry, to_global
WEIGHTS=[0,.05,.1,.2,.35,.5,.65,.8,.9,.95,1]

class Evaluator:
 def __init__(self,a,b,out):
  self.a=a;self.b=b;self.out=out;self.cache={};self.rows=[];self.start=time.monotonic()
  self.p=subprocess.Popen([str(binary()),str(a),str(b),'stream'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
  self.fields=self.p.stdout.readline().strip().split(',');self.file=(out/'evaluations.csv').open('w');self.writer=csv.DictWriter(self.file,fieldnames=self.fields+['level','scan']);self.writer.writeheader()
 def ev(self,q,level=3,scan=12):
  q=np.asarray(q,dtype=float);x,y=q
  if self.a==0 or self.b in (0,180):y=abs(y)
  if math.hypot(x,y)<1e-8:return None
  B=math.radians(self.b);gx=self.a+math.cos(B)*x-math.sin(B)*y;gy=math.sin(B)*x+math.cos(B)*y
  if math.hypot(gx,gy)>3300+1e-6:return None
  key=(round(float(x),10),round(float(y),10),level,scan)
  if key not in self.cache:
   self.p.stdin.write(f'{x:.16g} {y:.16g} {level} {scan}\n');self.p.stdin.flush();line=self.p.stdout.readline()
   if not line:raise RuntimeError('evaluator closed unexpectedly')
   r=dict(zip(self.fields,map(float,line.strip().split(','))));r.update(level=level,scan=scan)
   if not all(math.isfinite(v) for v in r.values()):raise RuntimeError(r)
   self.cache[key]=r;self.rows.append(r);self.writer.writerow(r)
   if len(self.rows)%100==0:self.file.flush()
  r=self.cache[key]
  return r if r['distance_K1']<=1500+1e-7 else None
 def score(self,q,w,level=3,scan=12):
  r=self.ev(q,level,scan)
  return score(r,w) if r else 1e10
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
 def close(self):
  self.file.close()
  try:
   self.p.stdin.close();self.p.wait(timeout=5)
  except (BrokenPipeError,subprocess.TimeoutExpired):
   self.p.kill();self.p.wait()


def score(r,w):
 # Only roundoff outside [0,1] is clipped for optimization; raw probability is saved.
 p=min(1.,max(0.,r['P_finish']));return (1-w)*r['J']/20+w*(1-p)

def best_spread(rows,w,n,distance):
 selected=[]
 for r in sorted(rows,key=lambda r:(score(r,w),r['J'])):
  q=np.array([r['x'],r['y']])
  if all(np.linalg.norm(q-np.array([z['x'],z['y']]))>distance for z in selected):selected.append(r)
  if len(selected)>=n:break
 return selected

def run(a,b,out,weights=None):
 b=float(b)%360
 weights=WEIGHTS if weights is None else list(weights)
 if not weights or any(not math.isfinite(w) or not 0<=w<=1 for w in weights):raise ValueError("weights must be in [0,1]")
 start=time.monotonic();name=f'a{a:g}_b{b:g}';info=initial_geometry(a,b);out=Path(out);out.mkdir(parents=True,exist_ok=False)
 (out/'initial_geometry.json').write_text(json.dumps(info,indent=2))
 qbase=info['center'];points=np.array(info['points']);span=float(np.ptp(points[:,0]));optima=[]
 if info['rho1']<=20:
  summary={'case':name,'a':a,'beta_deg':b,'status':'no_second_detection_needed','rho1':info['rho1'],'clear_center_global':info['center_global'],'weights':weights,'candidates':[]}
  (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True);return summary
 else:
  with Evaluator(a,b,out) as ev:
   basevalue=ev.ev(qbase,6,128)
   lo=points.min(0)-1501;hi=points.max(0)+1501
   gx=np.arange(math.floor(lo[0]/100)*100,hi[0]+100,100);gy=np.arange(math.floor(lo[1]/100)*100,hi[1]+100,100)
   if a==0 or b in (0,180):gy=gy[gy>=0]
   grid={(float(x),float(y)) for x in gx for y in gy}
   xmin=max(5.,points[:,0].min()-1);xmax=min(1500.,points[:,0].max()+1)
   step=max(2.,min(35.,span/20))
   yy=np.arange(-.8*span,.8*span+step,step)
   if a==0 or b in (0,180):yy=yy[yy>=0]
   grid|={(float(x),float(y)) for x in np.arange(xmin-.25*span,xmax+.25*span+step,step) for y in yy}
   grid|={(float(x),float(y)) for x in np.linspace(xmin,xmax,65) for y in [-30,-10,0,10,30]}
   for i,q in enumerate(sorted(grid)):
    ev.ev(q,2,6)
    if i%1000==0:print(name,'grid',i,'/',len(grid),'elapsed',round(time.monotonic()-start,1),flush=True)
   pool=[r for r in ev.rows if r['distance_K1']<=1500+1e-7]
   scan_weights=weights
   starts=[]
   for w in scan_weights:
    seeds=best_spread(pool,w,5,max(4.,span*.06))
    if basevalue is not None:seeds.append(basevalue)
    for r in seeds:
     q=[r['x'],r['y']]
     z,diag=minimize(lambda q:ev.score(q,w),q,step=min(25.,max(1.,span*.025)),xatol=.07,fatol=2e-7,maxiter=150)
     value=ev.ev(z)
     if value is not None:starts.append(dict(value,w=w,optimizer=diag));pool.append(value)
    print(name,'weight',w,'coarse best',min(score(r,w) for r in pool),'elapsed',round(time.monotonic()-start,1),flush=True)
   (out/'multistart.json').write_text(json.dumps(starts,indent=2))
   for w in scan_weights:
    finer=[]
    for r in best_spread(pool,w,2,max(1.,span*.002)):
     z,diag=minimize(lambda q:ev.score(q,w,4,24),[r['x'],r['y']],step=min(3.,max(.2,span*.003)),xatol=.015,fatol=2e-9,maxiter=130)
     finer.append(dict(ev.ev(z,6,128),w=w,optimizer=diag))
    best=min(finer,key=lambda r:(score(r,w),r['J']));optima.append(dict(best,F=score(best,w)))
    print(name,'refined',w,'q',round(best['x'],3),round(best['y'],3),'J',round(best['J'],6),'P',round(best['P_finish'],6),flush=True)
   # Choose the best among all high-precision candidates at each weight, including the initial enclosing-circle center.
   eligible=optima+([basevalue] if basevalue is not None else [])
   optima=[dict(min(eligible,key=lambda r:(score(r,w),r['J'])),w=w,F=min(score(r,w) for r in eligible)) for w in weights]
   # High precision checks around the final points at scales independent of the final simplex.
   neighbors=[]
   for w in scan_weights:
    r=next(r for r in optima if r['w']==w)
    for h in [.1,1.,5.]:
     for angle in np.arange(8)*math.pi/4:
      q=np.array([r['x'],r['y']])+h*np.array([math.cos(angle),math.sin(angle)])
      z=ev.ev(q,4,24)
      if z:neighbors.append(dict(z,w=w,step=h,F=score(z,w),improvement=score(r,w)-score(z,w)))
   (out/'neighbors.json').write_text(json.dumps(neighbors,indent=2))
 summary={'case':name,'a':a,'beta_deg':b,'initial_center_evaluation':basevalue,'weights':weights,'candidates':optima,'evaluation_count':len(ev.rows),'elapsed_seconds':time.monotonic()-start,'global_optimality_certified':False,'mirror_equivalence':a==0 or b in (0,180),'note':'Candidates are numerical optima from covering search and multistart refinement; continuous global optimality is not certified.'}
 summary['diagnostics']={'max_candidate_probability_residual':max(abs(r['probability_residual']) for r in optima),
                         'max_candidate_mec_gap_m':max(r['mec_gap'] for r in optima),
                         'candidate_depth_capped_count':sum(r['depth_capped'] for r in optima),
                         'max_neighbor_score_improvement':max([0.]+[r['improvement'] for r in neighbors])}
 candidate_points=[]
 for r in optima:
  candidate_points.append({'w':r['w'],'x_global':r['x_global'],'y_global':r['y_global'],'J':r['J'],'P_finish':r['P_finish'],'F':r['F'],'symmetry_copy':False})
  if summary['mirror_equivalence'] and abs(r['y'])>1e-7:
   x,y=to_global([r['x'],-r['y']],a,b)
   candidate_points.append({'w':r['w'],'x_global':x,'y_global':y,'J':r['J'],'P_finish':r['P_finish'],'F':r['F'],'symmetry_copy':True})
 with (out/'candidate_points.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(candidate_points[0]));writer.writeheader();writer.writerows(candidate_points)
 (out/'summary.json').write_text(json.dumps(summary,indent=2))
 with (out/'candidates.csv').open('w') as f:
  fields=['w','x_global','y_global','J','P_finish','P_onsite','F','probability_residual','distance_K1'];writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(optima)
 print('DONE',name,summary['evaluation_count'],'evaluations',round(summary['elapsed_seconds'],1),'seconds',flush=True)
 return summary

