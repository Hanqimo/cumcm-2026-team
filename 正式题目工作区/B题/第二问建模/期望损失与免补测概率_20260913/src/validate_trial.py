"""Integral convergence, old-objective regression and independent ray/support-circle geometry."""
from pathlib import Path
import csv,importlib.util,itertools,json,math,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ray_checks',ROOT/'inputs/base_validate.py');rays=importlib.util.module_from_spec(spec);spec.loader.exec_module(rays)

def call(a,b,args):return subprocess.check_output([str(ROOT/'solver'),str(a),str(b),*map(str,args)],text=True)
def evalpoint(a,b,q,level,scan):return {k:float(v) for k,v in next(csv.DictReader(call(a,b,['eval',*q,level,scan]).splitlines())).items()}
def exact_finite_radius(v):
 if len(v)<2:return 0.
 v=v-v.mean(axis=0);n=len(v);pairs=np.array(list(itertools.combinations(range(n),2)))
 cc=(v[pairs[:,0]]+v[pairs[:,1]])*.5;rr=np.sum((v[pairs[:,0]]-cc)**2,axis=1)
 if n>=3:
  tri=np.array(list(itertools.combinations(range(n),3)));a=v[tri[:,0]];b=v[tri[:,1]]-a;c=v[tri[:,2]]-a
  det=2*(b[:,0]*c[:,1]-b[:,1]*c[:,0]);ok=abs(det)>1e-12;a=a[ok];b=b[ok];c=c[ok];det=det[ok]
  b2=(b*b).sum(1);c2=(c*c).sum(1);z=np.c_[(b2*c[:,1]-b[:,1]*c2)/det,(b[:,0]*c2-b2*c[:,0])/det]
  cc=np.r_[cc,a+z];rr=np.r_[rr,(z*z).sum(1)]
 for i in np.argsort(rr):
  if np.max(((cc[i]-v)**2).sum(1)-rr[i])<=1e-8:return math.sqrt(float(rr[i]))
 raise RuntimeError('no enclosing circle')

def main():
 convergence=[];geometries=[];symmetries=[]
 for file in sorted((ROOT/'results').glob('*/summary.json')):
  case=json.loads(file.read_text());a,b=case['a'],case['beta_deg'];rows=case['candidates'];weights=[0,.2,.5,.8,1] if a==0 else [0]
  for w in weights:
   r=next(r for r in rows if r['w']==w);q=[r['x'],r['y']]
   levels=[evalpoint(a,b,q,level,scan) for level,scan in [(4,32),(5,64),(6,128)]]
   ref=levels[-1];original=float(call(a,b,['baseline',*q,6]));record={'case':case['case'],'w':w,'levels':levels,'J_baseline_kernel':original,'J_regression_difference':ref['J']-original,'J_convergence_difference':ref['J']-levels[-2]['J'],'P_convergence_difference':ref['P_finish']-levels[-2]['P_finish']};convergence.append(record)
   assert abs(record['J_regression_difference'])<2e-5,record
   assert abs(record['J_convergence_difference'])<1e-5,record
   assert abs(record['P_convergence_difference'])<2e-6,record
   assert abs(ref['probability_residual'])<1e-7,ref
   assert -1e-7<=ref['P_finish']<=1+1e-7 and ref['P_finish']>=ref['P_onsite']-1e-7 and ref['P_finish']>=ref['P_H']-1e-7,ref
   if b in (0,180):
    mirror=evalpoint(a,b,[q[0],-q[1]],5,64);symmetries.append({'case':case['case'],'w':w,'J_difference':mirror['J']-r['J'],'P_difference':mirror['P_finish']-r['P_finish']});assert abs(mirror['J']-r['J'])<1e-5 and abs(mirror['P_finish']-r['P_finish'])<2e-6
   # Sample both sides of all rho=20 events plus representative interval midpoints.
   cuts=json.loads(call(a,b,['cuts',*q,128]));angles=[]
   for t in cuts:
    geo=json.loads(call(a,b,['geometry',*q,1,t]))
    if abs(geo['radius_upper']-20)<1e-3:angles.extend([t-1e-5,t+1e-5])
   mids=[(l+h)/2 for l,h in zip(cuts[:-1],cuts[1:])]
   if mids:angles += [mids[i] for i in np.linspace(0,len(mids)-1,min(4,len(mids))).astype(int)]
   # Geometry uses independently constructed radial intersections, not main boundary arcs.
   for kind,theta in [(1,t) for t in angles]+[(0,0),(2,0)]:
    geo=json.loads(call(a,b,['geometry',*q,kind,theta]));points=rays.independent_points(a,b,q,kind,theta,n=16001)
    if not len(points):continue
    directions=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)]
    v=points[np.unique([int(np.argmax(points@u)) for u in directions])]
    low=exact_finite_radius(v);high=geo['radius_upper'];outside=float(np.linalg.norm(points-np.array(geo['center']),axis=1).max()-high)
    g={'case':case['case'],'w':w,'kind':kind,'theta':theta,'sample_count':len(points),'support_points':len(v),'independent_radius_lower':low,'main_radius_upper':high,'radius_gap':high-low,'max_sample_outside':outside,'completion_decisive':high<=20 or low>20}
    geometries.append(g);assert outside<2e-5 and high>=low-2e-5,g
   print('validated',case['case'],w,'J diff',record['J_convergence_difference'],'P diff',record['P_convergence_difference'],flush=True)
   (ROOT/'verification/convergence.json').write_text(json.dumps(convergence,indent=2));(ROOT/'verification/independent_geometry.json').write_text(json.dumps(geometries,indent=2))
 (ROOT/'verification/symmetry.json').write_text(json.dumps(symmetries,indent=2))
 sims=json.loads((ROOT/'verification/joint_prior_simulation.json').read_text())
 for s in sims:assert s['invalid']==0 and abs(s['J_zscore'])<4 and abs(s['P_finish_zscore'])<4,s
 summary={'checked_points':len(convergence),'independent_geometry_checks':len(geometries),'max_J_regression_difference':max(abs(r['J_regression_difference']) for r in convergence),'max_J_convergence_difference':max(abs(r['J_convergence_difference']) for r in convergence),'max_P_convergence_difference':max(abs(r['P_convergence_difference']) for r in convergence),'max_probability_residual':max(abs(r['levels'][-1]['probability_residual']) for r in convergence),'max_sample_outside':max(r['max_sample_outside'] for r in geometries),'max_independent_radius_gap':max(r['radius_gap'] for r in geometries),'ambiguous_completion_checks':sum(not r['completion_decisive'] for r in geometries),'simulation_samples':sum(r['n'] for r in sims),'max_simulation_J_zscore':max(abs(r['J_zscore']) for r in sims),'max_simulation_P_zscore':max(abs(r['P_finish_zscore']) for r in sims),'status':'PASS','limitations':'Finite independent samples provide lower bounds and sampled containment only; convergence is empirical. Simulation shares MEC kernel and independently validates probabilities, not geometry. No nonzero global optimum certificate.'}
 ns=evalpoint(1700,0,[-930,0],6,128);geo=json.loads(call(1700,0,['geometry',-930,0,2,0]))
 assert ns['P_N']>0 and abs(ns['P_finish_N']-ns['P_N'])<1e-10 and geo['radius_upper']<20 and geo['dmax']>1000
 (ROOT/'verification/no_signal_completion_case.json').write_text(json.dumps({'a':1700,'beta_deg':0,'q_local':[-930,0],'q_global':[770,0],'evaluation':ns,'no_signal_geometry':geo,'check':'No signal can finish bearing localization after moving: P_finish_N=P_N, rho_N<20, current point farther than 1000m.','status':'PASS'},indent=2))
 summary['no_signal_completion_branch_checked']=True
 (ROOT/'verification/summary.json').write_text(json.dumps(summary,indent=2));print(summary)

if __name__=='__main__':main()
