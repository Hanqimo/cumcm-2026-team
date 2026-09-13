"""Bounded covering search and weighted multistart refinement. No adopted files are written."""
from pathlib import Path
import argparse,csv,importlib.util,json,math,subprocess,time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('frozen_search',ROOT/'inputs/base_search.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
WEIGHTS=[0,.05,.1,.2,.35,.5,.65,.8,.9,.95,1]

class Evaluator:
 def __init__(self,a,b,out):
  self.a=a;self.b=b;self.out=out;self.cache={};self.rows=[];self.start=time.monotonic()
  self.p=subprocess.Popen([str(ROOT/'solver'),str(a),str(b),'stream'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
  self.fields=self.p.stdout.readline().strip().split(',');self.file=(out/'evaluations.csv').open('w');self.writer=csv.DictWriter(self.file,fieldnames=self.fields+['level','scan']);self.writer.writeheader()
 def ev(self,q,level=3,scan=12):
  q=np.asarray(q,dtype=float);x,y=q
  if self.b in (0,180):y=abs(y)
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
 def close(self):self.file.close();self.p.stdin.close();self.p.wait(timeout=5)

def score(r,w):
 # Only roundoff outside [0,1] is clipped for optimization; raw probability is saved.
 p=min(1.,max(0.,r['P_finish']));return (1-w)*r['J']/20+w*(1-p)+(1e-10*r['J']/20 if w==1 else 0)

def best_spread(rows,w,n,distance):
 selected=[]
 for r in sorted(rows,key=lambda r:(score(r,w),r['J'])):
  q=np.array([r['x'],r['y']])
  if all(np.linalg.norm(q-np.array([z['x'],z['y']]))>distance for z in selected):selected.append(r)
  if len(selected)>=n:break
 return selected

def run(a,b):
 start=time.monotonic();name=f'a{a:g}_b{b:g}';out=ROOT/'results'/name;out.mkdir(exist_ok=False)
 baseline=json.loads((ROOT/'inputs'/f'{name}_baseline.json').read_text());info=baseline['initial_geometry'];ev=Evaluator(a,b,out)
 base=baseline['best']['radius'];qbase=[base['x'],base['y']]
 basevalue=ev.ev(qbase,5,64);print(name,'baseline',basevalue,flush=True)
 points=np.array(info['points']);span=points[:,0].max()-points[:,0].min();optima=[]
 if info['rho1']<=20:
  r=ev.ev(info['center'],5,64)
  assert r['J']<1e-8 and abs(r['P_finish']-1)<2e-7
  optima=[dict(r,w=w,F=score(r,w),reason='J=0 and P_finish=1: simultaneous global bounds attained') for w in WEIGHTS]
 else:
  lo=points.min(0)-1501;hi=points.max(0)+1501
  gx=np.arange(math.floor(lo[0]/100)*100,hi[0]+100,100);gy=np.arange(math.floor(lo[1]/100)*100,hi[1]+100,100)
  if b in (0,180):gy=gy[gy>=0]
  grid={(float(x),float(y)) for x in gx for y in gy}
  xmin=max(5.,points[:,0].min()-1);xmax=min(1500.,points[:,0].max()+1)
  step=max(2.,min(35.,span/20))
  yy=np.arange(-.8*span,.8*span+step,step)
  if b in (0,180):yy=yy[yy>=0]
  grid|={(float(x),float(y)) for x in np.arange(xmin-.25*span,xmax+.25*span+step,step) for y in yy}
  grid|={(float(x),float(y)) for x in np.linspace(xmin,xmax,65) for y in [-30,-10,0,10,30]}
  for i,q in enumerate(sorted(grid)):
   ev.ev(q,2,6)
   if i%1000==0:print(name,'grid',i,'/',len(grid),'elapsed',round(time.monotonic()-start,1),flush=True)
  pool=[r for r in ev.rows if r['distance_K1']<=1500+1e-7]
  # A point with both the best radius loss and P_finish=1 cannot benefit from probability weighting.
  # Still refine J from independent covering-grid seeds before using this dominance argument.
  scan_weights=WEIGHTS if basevalue['P_finish']<1-1e-7 else [0]
  starts=[]
  for w in scan_weights:
   seeds=best_spread(pool,w,5,max(4.,span*.06))
   seeds.append(basevalue)
   for r in seeds:
    q=[r['x'],r['y']]
    z,diag=old.minimize(lambda q:ev.score(q,w),q,step=min(25.,max(1.,span*.025)),xatol=.07,fatol=2e-7,maxiter=150)
    value=ev.ev(z);starts.append(dict(value,w=w,optimizer=diag));pool.append(value)
   print(name,'weight',w,'coarse best',min(score(r,w) for r in pool),'elapsed',round(time.monotonic()-start,1),flush=True)
  (out/'multistart.json').write_text(json.dumps(starts,indent=2))
  for w in scan_weights:
   finer=[]
   for r in best_spread(pool,w,2,max(1.,span*.002)):
    z,diag=old.minimize(lambda q:ev.score(q,w,4,24),[r['x'],r['y']],step=min(3.,max(.2,span*.003)),xatol=.015,fatol=2e-9,maxiter=130)
    finer.append(dict(ev.ev(z,5,64),w=w,optimizer=diag))
   best=min(finer,key=lambda r:(score(r,w),r['J']));optima.append(dict(best,F=score(best,w)))
   print(name,'refined',w,'q',round(best['x'],3),round(best['y'],3),'J',round(best['J'],6),'P',round(best['P_finish'],6),flush=True)
  if len(scan_weights)==1:
   best=optima[0]
   if best['P_finish']<1-1e-7:raise RuntimeError('Dominance shortcut invalid after J refinement')
   optima=[dict(best,w=w,F=score(best,w),reason='same best J candidate attains upper bound P_finish=1') for w in WEIGHTS]
  # Choose the best among all high-precision candidates at each weight, including the baseline.
  eligible=optima+[basevalue]
  optima=[dict(min(eligible,key=lambda r:(score(r,w),r['J'])),w=w,F=min(score(r,w) for r in eligible)) for w in WEIGHTS]
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
 ev.close()
 summary={'case':name,'a':a,'beta_deg':b,'baseline':basevalue,'weights':WEIGHTS,'candidates':optima,'evaluation_count':len(ev.rows),'elapsed_seconds':time.monotonic()-start,'global_optimality_certified':info['rho1']<=20,'mirror_equivalence':b in (0,180),'note':'Candidates are numerical optima from covering search and multistart refinement; only simultaneous J=0/P=1 is a global certificate.'}
 (out/'summary.json').write_text(json.dumps(summary,indent=2))
 with (out/'candidates.csv').open('w') as f:
  fields=['w','x_global','y_global','J','P_finish','P_onsite','F','probability_residual','distance_K1'];writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(optima)
 print('DONE',name,summary['evaluation_count'],'evaluations',round(summary['elapsed_seconds'],1),'seconds',flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--a',type=float,default=0);parser.add_argument('--beta',type=float,default=0);args=parser.parse_args();run(args.a,args.beta)
