from pathlib import Path
import json,csv,math,subprocess,importlib.util,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('independent',ROOT/'src/validate_trial.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
def call(a,b,*args):return subprocess.check_output([str(ROOT/'solver'),str(a),str(b),*map(str,args)],text=True)
def ev(a,b,q,level=6,scan=128):return {k:float(v) for k,v in next(csv.DictReader(call(a,b,'eval',*q,level,scan).splitlines())).items()}
origin=json.loads((ROOT/'inputs/a0_b0_weighted_reference.json').read_text());edge=json.loads((ROOT/'inputs/a1700_b0_weighted_reference.json').read_text())
checks=[];geometries=[];simulations=[];general=[]
for a,b,s in [(0,0,origin),(1200,30,json.loads((ROOT/'results/a1200_b30/summary.json').read_text())),(1200,90,json.loads((ROOT/'results/a1200_b90/summary.json').read_text())),(1700,0,edge)]:
 r=next(z for z in s['candidates'] if z['w']==.5);q=[r['x'],r['y']];v=ev(a,b,q)
 assert abs(v['probability_residual'])<1e-7
 assert abs(v['J']-r['J'])<1e-4 and abs(v['P_finish']-r['P_finish'])<1e-6
 row={'a_m':a,'beta_deg':b,'w':.5,'q_x_m':v['x_global'],'q_y_m':v['y_global'],'J_m':v['J'],'P_finish':v['P_finish'],'P_onsite':v['P_onsite'],'source':'existing verified run' if a!=1200 else 'new covering search'};general.append(row)
 if a==1200:
  checks.append({'a':a,'beta':b,'J_refinement_difference':v['J']-r['J'],'P_refinement_difference':v['P_finish']-r['P_finish'],'probability_residual':v['probability_residual'],'final_eval':v})
  cuts=json.loads(call(a,b,'cuts',*q,128));mids=[(l+h)/2 for l,h in zip(cuts[:-1],cuts[1:])];angles=[mids[i] for i in np.linspace(0,len(mids)-1,min(10,len(mids))).astype(int)]
  for theta in angles:
   g=json.loads(call(a,b,'geometry',*q,1,theta));p=ind.rays.independent_points(a,b,q,1,theta,n=16001)
   if not len(p):continue
   directions=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)];support=p[np.unique([int(np.argmax(p@u)) for u in directions])]
   lower=ind.exact_finite_radius(support);upper=g['radius_upper'];outside=float(np.linalg.norm(p-np.array(g['center']),axis=1).max()-upper)
   assert outside<2e-5 and upper>=lower-2e-5 and upper-lower<.01
   geometries.append({'a':a,'beta':b,'theta':theta,'samples':len(p),'independent_lower_m':lower,'kernel_upper_m':upper,'gap_m':upper-lower,'outside_m':outside})
  sim=json.loads(call(a,b,'mc',*q,20000,20260913+b));sim.update(a=a,beta_deg=b,J_reference=v['J'],P_reference=v['P_finish'])
  sim['J_zscore']=(sim['J_mean']-v['J'])/sim['J_se'];sim['P_zscore']=(sim['P_finish']-v['P_finish'])/sim['P_finish_se'] if sim['P_finish_se'] else 0
  assert sim['invalid']==0 and abs(sim['J_zscore'])<4 and abs(sim['P_zscore'])<4
  simulations.append(sim)
  print('Validated',a,b,row,flush=True)
# At beta=150 the whole original first-observation sector remains inside Omega.
# Squared distance is convex in r, and cos is maximized at the endpoint 149 degrees.
radii=[5,1500];maxdist=max(math.hypot(1200+r*math.cos(math.radians(150+d)),r*math.sin(math.radians(150+d))) for r in radii for d in [-1,1]);assert maxdist<1800
r=next(z for z in origin['candidates'] if z['w']==.5);q=[r['x'],-r['y']];v=ev(1200,150,q)
assert abs(v['J']-r['J'])<1e-6 and abs(v['P_finish']-r['P_finish'])<1e-7
general.insert(3,{'a_m':1200,'beta_deg':150,'w':.5,'q_x_m':v['x_global'],'q_y_m':v['y_global'],'J_m':v['J'],'P_finish':v['P_finish'],'P_onsite':v['P_onsite'],'source':'rotation/translation of origin solution; no clipping of initial sector'})
# Check that reported one-decimal global coordinates reproduce displayed metric precision.
rounding=[]
for row in general:
 qg=np.round([row['q_x_m'],row['q_y_m']],1);B=math.radians(row['beta_deg']);p=qg-np.array([row['a_m'],0]);ql=[math.cos(B)*p[0]+math.sin(B)*p[1],-math.sin(B)*p[0]+math.cos(B)*p[1]];v=ev(row['a_m'],row['beta_deg'],ql)
 rounding.append({'case':[row['a_m'],row['beta_deg']],'q_global_rounded':qg.tolist(),'J_difference_m':v['J']-row['J_m'],'P_difference':v['P_finish']-row['P_finish']})
 assert abs(v['J']-row['J_m'])<.005 and abs(v['P_finish']-row['P_finish'])<.00005
for name,rows in [('typical_cases',general),('origin_weights',[{'w':z['w'],'q_x_m':z['x_global'],'q_abs_y_m':abs(z['y_global']),'J_m':z['J'],'P_finish':z['P_finish']} for z in origin['candidates']])]:
 with (ROOT/f'results/{name}.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(ROOT/'verification/numerical_checks.json').write_text(json.dumps({'refinement':checks,'independent_geometry':geometries,'simulations':simulations,'coordinate_rounding':rounding,'inward_sector_max_target_distance_m':maxdist,'equivalent_inward_case_verified':True,'global_optimality_certified':False,'MC_scope':'Joint-prior sampling checks integration; geometry is shared in MC and separately checked with independent rays and support circles.'},indent=2))
print('DONE',len(general),'typical cases;',len(geometries),'independent geometries;',sum(z['n'] for z in simulations),'simulation samples',flush=True)
