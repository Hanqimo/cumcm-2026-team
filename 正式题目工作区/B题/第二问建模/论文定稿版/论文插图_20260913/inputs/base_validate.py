"""Convergence, independent polar-ray containment, and joint-prior Monte Carlo.
The C++ MEC kernel is reused by MC; MC validates probability integration, not MEC geometry.
"""
from pathlib import Path
import math,json,csv,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];EXE=str(ROOT/'solver');A=math.pi/180

def run(a,b,args):return subprocess.check_output([EXE,str(a),str(b)]+list(map(str,args)),text=True)
def evaluate(a,b,q,lev):return {k:float(v) for k,v in next(csv.DictReader(run(a,b,['eval',*q,lev]).splitlines())).items()}
def independent_points(a,b,q,kind,t,n=8001):
 phi=np.linspace(-A,A,n);u=np.c_[np.cos(phi),np.sin(phi)];q=np.array(q);B=math.radians(b);center=np.array([-a*math.cos(B),a*math.sin(B)])
 cuts=[np.full(n,5.),np.full(n,1500.)]
 def circlecuts(c,r):
  proj=u@c;disc=proj*proj+r*r-c@c;h=np.sqrt(np.maximum(0,disc));good=disc>=0
  cuts.extend([np.where(good,proj-h,np.nan),np.where(good,proj+h,np.nan)])
 circlecuts(center,1800)
 for r in ([5] if kind==0 else [1000] if kind==2 else [5,1500]):circlecuts(q,r)
 if kind==2:
  v=u@q;cuts.append(np.divide(q@q,2*v,out=np.full(n,np.nan),where=abs(v)>1e-12))
 if kind==1:
  for ang in [t-A,t+A]:
   v=np.array([math.cos(ang),math.sin(ang)]);den=u[:,0]*v[1]-u[:,1]*v[0];num=q[0]*v[1]-q[1]*v[0]
   cuts.append(np.divide(num,den,out=np.full(n,np.nan),where=abs(den)>1e-12))
 rr=np.sort(np.stack(cuts,axis=1),axis=1);lo=rr[:,:-1];hi=rr[:,1:];mid=(lo+hi)/2
 g=u[:,None,:]*mid[:,:,None];d=np.linalg.norm(g-q,axis=2)
 ok=np.isfinite(mid)&(lo>=5-1e-8)&(hi<=1500+1e-8)&(hi-lo>1e-9)&(np.linalg.norm(g-center,axis=2)<=1800+1e-8)
 if kind==0:ok&=d<=5+1e-8
 elif kind==2:ok&=(d>=1000-1e-8)&(d>=mid-1e-8)
 else:
  ang=np.arctan2(g[:,:,1]-q[1],g[:,:,0]-q[0]);delta=np.arctan2(np.sin(ang-t),np.cos(ang-t));ok&=(d>=5-1e-8)&(d<=1500+1e-8)&(abs(delta)<=A+1e-10)
 return np.concatenate([(u[:,None,:]*lo[:,:,None])[ok],(u[:,None,:]*hi[:,:,None])[ok]])

def checkgeometry(a,b,q,kind,theta):
 geo=json.loads(run(a,b,['geometry',*q,kind,theta]));p=independent_points(a,b,q,kind,theta)
 out={'a':a,'beta_deg':b,'q_local':q,'kind':kind,'theta':theta,'independent_sample_count':len(p),'cpp_arc_count':len(geo['arcs'])}
 if not len(p):return out
 c=np.array(geo['center']);r=geo['radius_upper'];dist=np.linalg.norm(p-c,axis=1)
 dirs=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)];ids=np.unique([int(np.argmax(p@v)) for v in dirs]);v=p[ids]
 low=np.linalg.norm(v[:,None,:]-v[None,:,:],axis=2).max()/2
 out.update(radius_upper=r,diameter_lower=float(low),radius_gap=float(r-low),max_sample_outside=float(dist.max()-r),dmax_cpp=geo['dmax'],dmax_sample=float(np.linalg.norm(p-np.array(q),axis=1).max()),internal_mec_gap=r-geo['radius_lower'])
 assert out['max_sample_outside']<1e-5,out
 return out

def main():
 records=[];georecords=[];mc=[];comparison=[];old=json.loads((ROOT/'inputs/baseline_reference.json').read_text())
 for file in sorted((ROOT/'results').glob('*/summary.json')):
  case=json.loads(file.read_text());a=case['a_m'];b=case['beta_deg'];name=file.parent.name
  for obj,best in case['best'].items():
   q=[best['x'],best['y']];vals=[]
   for lev in [3,4,5,6]:
    v=evaluate(a,b,q,lev);v.update(case=name,objective=obj,level=lev);vals.append(v);records.append(v)
   ref=vals[-1];assert abs(ref['P_H']+ref['P_N']+ref['P_A']-1)<2e-6,(name,ref)
   assert ref['P_loc']<=1+2e-6
   assert ref['J']+1e-7>=math.pi*ref['E_radius_loss']**2
   profile=ROOT/'verification'/f'{name}_{obj}_profile.csv'
   subprocess.run([EXE,str(a),str(b),'profile',*map(str,q),'4',str(profile)],check=True)
   pro=list(csv.DictReader(profile.open()));idx=np.linspace(0,len(pro)-1,min(9,len(pro))).astype(int)
   for i in idx:georecords.append(checkgeometry(a,b,q,1,float(pro[i]['theta'])))
   for kind in [0,2]:georecords.append(checkgeometry(a,b,q,kind,0))
   if obj=='area' or np.linalg.norm(q-np.array([case['best']['area']['x'],case['best']['area']['y']]))>.1:
    sim=json.loads(run(a,b,['mc',*q,20000,20260912+(obj=='radius')]))
    sim.update(case=name,objective=obj,reference_area=ref['J'],reference_radius=ref['E_radius_loss'])
    sim['area_zscore']=(sim['mean_area']-ref['J'])/sim['standard_error'] if sim['standard_error']>0 else 0
    sim['radius_zscore']=(sim['mean_radius']-ref['E_radius_loss'])/sim['radius_standard_error'] if sim['radius_standard_error']>0 else 0
    assert sim['invalid']==0 and sim['max_truth_coverage_residual']<1e-5,sim
    mc.append(sim)
   if a==0 and b==0:
    previous=old[obj];qold=previous['point_north_m'];evold=evaluate(0,0,qold,6)
    comparison.append({'objective':obj,'old_q':qold,'new_q':q,'coordinate_difference_after_reflection_m':math.hypot(q[0]-qold[0],abs(q[1])-qold[1]),'old_saved_area':previous['expected_area_loss_m2'],'old_saved_radius':previous['expected_radius_loss_m'],'new_solver_at_old_point':evold,'new_solver_at_new_point':ref,'area_difference_at_old_point':evold['J']-previous['expected_area_loss_m2'],'radius_difference_at_old_point':evold['E_radius_loss']-previous['expected_radius_loss_m']})
   print('validated',name,obj,'mass residual',ref['P_H']+ref['P_N']+ref['P_A']-1,flush=True)
  (ROOT/'verification/convergence.json').write_text(json.dumps(records,indent=2))
  (ROOT/'verification/independent_geometry.json').write_text(json.dumps(georecords,indent=2))
  (ROOT/'verification/joint_prior_mc.json').write_text(json.dumps(mc,indent=2))
  (ROOT/'verification/origin_regression.json').write_text(json.dumps(comparison,indent=2))
 out={'cases':len(set(r['case'] for r in records)),'geometry_checks':len(georecords),'max_containment_residual_m':max(x.get('max_sample_outside',-1e99) for x in georecords),'max_mc_area_zscore':max(abs(x['area_zscore']) for x in mc),'max_mc_radius_zscore':max(abs(x['radius_zscore']) for x in mc),'max_probability_sum_residual':max(abs(x['P_H']+x['P_N']+x['P_A']-1) for x in records if x['level']==6),'note':'Geometry uses independent polar interval samples. MC shares MEC evaluator; coverage and integration claims are separate.'}
 (ROOT/'verification/summary.json').write_text(json.dumps(out,indent=2));print(out)
if __name__=='__main__':main()
