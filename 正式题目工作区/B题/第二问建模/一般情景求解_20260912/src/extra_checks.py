"""Independent exhaustive finite support-circle lower bounds and symmetry checks."""
from pathlib import Path
import json,math,itertools,subprocess
import numpy as np
from validate_general import ROOT,evaluate,independent_points

def exhaustive_radius(v):
 # Enumerate all 2-point diameter circles and 3-point circumcircles. Different from incremental C++ MEC.
 if len(v)<2:return 0.
 v=v-v.mean(axis=0);n=len(v);pairs=np.array(list(itertools.combinations(range(n),2)))
 cc=(v[pairs[:,0]]+v[pairs[:,1]])*.5;rr=np.sum((v[pairs[:,0]]-cc)**2,axis=1)
 if n>=3:
  tri=np.array(list(itertools.combinations(range(n),3)));a=v[tri[:,0]];b=v[tri[:,1]]-a;c=v[tri[:,2]]-a
  det=2*(b[:,0]*c[:,1]-b[:,1]*c[:,0]);ok=abs(det)>1e-12;a=a[ok];b=b[ok];c=c[ok];det=det[ok]
  b2=(b*b).sum(1);c2=(c*c).sum(1);z=np.c_[(b2*c[:,1]-b[:,1]*c2)/det,(b[:,0]*c2-b2*c[:,0])/det]
  cc=np.r_[cc,a+z];rr=np.r_[rr,(z*z).sum(1)]
 ids=np.argsort(rr)
 for off in range(0,len(ids),512):
  idx=ids[off:off+512];d2=((cc[idx,None,:]-v[None,:,:])**2).sum(2);good=np.max(d2-rr[idx,None],axis=1)<=1e-8
  if np.any(good):return math.sqrt(float(rr[idx[np.flatnonzero(good)[0]]]))
 raise RuntimeError('No enclosing candidate circle')

def main():
 previous=json.loads((ROOT/'verification/independent_geometry.json').read_text());checks=[]
 for row in previous:
  if row.get('radius_gap',0)<.001:continue
  a,b,q,k,t=row['a'],row['beta_deg'],row['q_local'],row['kind'],row['theta']
  p=independent_points(a,b,q,k,t,n=40001);dirs=np.c_[np.cos(np.arange(128)*math.pi/64),np.sin(np.arange(128)*math.pi/64)];v=p[np.unique([np.argmax(p@z) for z in dirs])]
  low=exhaustive_radius(v);r=dict(row,refined_sample_count=len(p),extreme_points=len(v),exhaustive_circle_lower=low,refined_radius_gap=row['radius_upper']-low)
  assert -.00001<=r['refined_radius_gap']<.01,r;checks.append(r)
 (ROOT/'verification/exhaustive_support_circles.json').write_text(json.dumps(checks,indent=2))
 sym=[]
 for a,b in [(1700,90),(2500,150)]:
  case=json.loads((ROOT/f'results/a{a}_b{b}/summary.json').read_text())
  for obj,best in case['best'].items():
   q=[best['x'],best['y']];one=evaluate(a,b,q,6);two=evaluate(a,-b,[q[0],-q[1]],6)
   r={'a':a,'beta_deg':b,'objective':obj,'area_difference':two['J']-one['J'],'radius_difference':two['E_radius_loss']-one['E_radius_loss']};sym.append(r)
   assert abs(r['area_difference'])<1e-6 and abs(r['radius_difference'])<1e-8,r
 for obj in ['area','radius']:
  row=json.loads((ROOT/'results/a0_b0/summary.json').read_text())['best'][obj];q=[row['x'],row['y']];one=evaluate(0,0,q,6);two=evaluate(900,90,q,6)
  sym.append({'type':'inactive disk clipping: origin vs a900,b90','objective':obj,'area_difference':two['J']-one['J'],'radius_difference':two['E_radius_loss']-one['E_radius_loss']})
 (ROOT/'verification/symmetry.json').write_text(json.dumps(sym,indent=2))
 print({'exhaustive_cases':len(checks),'largest_refined_gap':max(x['refined_radius_gap'] for x in checks),'symmetry':sym})
if __name__=='__main__':main()
