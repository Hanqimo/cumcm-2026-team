"""Explicitly audit opposite-side basins, and preserve all original search records."""
from pathlib import Path
import csv,json,subprocess,math
from search_general import ROOT, SOLVER,minimize

def run():
 allchecks=[]
 for f in sorted((ROOT/'results').glob('*/summary.json')):
  case=json.loads(f.read_text());a,b=case['a_m'],case['beta_deg'];prefix=[SOLVER,str(a),str(b)]
  if case['global_optimality_proven']:continue
  rows=[{k:float(v) for k,v in x.items()} for x in csv.DictReader((f.parent/'central_grid.csv').open())]
  cache={}
  def ev(q,lev):
   key=(*map(float,q),lev)
   if key not in cache:cache[key]={k:float(v) for k,v in next(csv.DictReader(subprocess.check_output(prefix+['eval',*map(str,q),str(lev)],text=True).splitlines())).items()}
   return cache[key]
  for obj,col in [('area','J'),('radius','E_radius_loss')]:
   checks=[]
   for sign in [-1,1]:
    seed=min((r for r in rows if r['y']*sign>0),key=lambda x:x[col]);q=[seed['x'],seed['y']]
    q,diag=minimize(lambda q:ev(q,3)[col],q,step=10,xatol=.05,fatol=1e-7,maxiter=100)
    q,diag=minimize(lambda q:ev(q,5)[col],q,step=1,xatol=.003,fatol=1e-9,maxiter=100)
    r=dict(ev(q,5),case=f.parent.name,objective=obj,start_side=sign,optimizer=diag,level=5);checks.append(r);allchecks.append(r)
   (f.parent/f'{obj}_side_audit.json').write_text(json.dumps(checks,indent=2))
   v=min(checks,key=lambda r:r[col]);old=case['best'][obj]
   # Changes below this reporting tolerance are retained only as numerical ties.
   tol=1e-5 if obj=='area' else 1e-7
   if v[col]<old[col]-tol:
    (f.parent/f'{obj}_before_audit.json').write_text(json.dumps(old,indent=2));case['best'][obj]=v;case['status']+='; improved by opposite-side audit';f.write_text(json.dumps(case,indent=2))
    print('IMPROVED',f.parent.name,obj,old[col],v[col],flush=True)
   else:print('AUDIT',f.parent.name,obj,[(r['start_side'],r[col]) for r in checks],flush=True)
 (ROOT/'verification/opposite_side_search.json').write_text(json.dumps(allchecks,indent=2))
if __name__=='__main__':run()
