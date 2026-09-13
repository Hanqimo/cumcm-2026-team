from pathlib import Path
import csv,importlib.util,json,math,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ind',ROOT/'src/independent_geometry.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
def call(a,b,*args):return subprocess.check_output([str(ROOT/'solver'),str(a),str(b),*map(str,args)],text=True)
def ev(a,b,q,level=6,scan=128):return {k:float(v) for k,v in next(csv.DictReader(call(a,b,'eval',*q,level,scan).splitlines())).items()}
def dump(name,obj):(ROOT/f'verification/{name}.json').write_text(json.dumps(obj,indent=2))
checks=[];geo=[];sims=[];rounding=[];allrows=[];cases=[]
for file in sorted((ROOT/'results').glob('*/summary.json')):
 case=json.loads(file.read_text());a,b=case['a'],case['beta_deg'];name=case['case'];candidates=case['candidates'];verified=[]
 if not candidates:cases.append({'case':name,'status':case['status'],'rho1':case['rho1']});continue
 for r in candidates:
  w=r['w'];q=[r['x'],r['y']];v=ev(a,b,q);row={**v,'w':w,'a_m':a,'beta_deg':b};verified.append(row)
  c={'case':name,'w':w,'J_difference_m':v['J']-r['J'],'P_difference':v['P_finish']-r['P_finish'],'probability_residual':v['probability_residual']};checks.append(c)
  assert abs(c['J_difference_m'])<1e-4 and abs(c['P_difference'])<2e-6 and abs(c['probability_residual'])<1e-7,c
  assert 0<=v['J'] and -1e-7<=v['P_finish']<=1+1e-7
  if a==0 or w==.5:
   globalq=np.round([v['x_global'],v['y_global']],1);t=math.radians(b);d=globalq-[a,0];ql=[math.cos(t)*d[0]+math.sin(t)*d[1],-math.sin(t)*d[0]+math.cos(t)*d[1]];rv=ev(a,b,ql)
   rd={'case':name,'w':w,'rounded_global_q':globalq.tolist(),'J_difference_m':rv['J']-v['J'],'P_difference':rv['P_finish']-v['P_finish']};rounding.append(rd)
   assert abs(rd['J_difference_m'])<.005 and abs(rd['P_difference'])<.00005,rd
  if w not in ([0,.5,1] if a==0 else [.5]):continue
  if b==0:
   mirror=ev(a,b,[q[0],-q[1]]);assert abs(v['J']-mirror['J'])<1e-5 and abs(v['P_finish']-mirror['P_finish'])<2e-6
  cuts=json.loads(call(a,b,'cuts',*q,128));angles=[]
  for t in cuts:
   g=json.loads(call(a,b,'geometry',*q,1,t))
   if abs(g['radius_upper']-20)<1e-3:angles.extend([t-1e-5,t+1e-5])
  mids=[(l+h)/2 for l,h in zip(cuts[:-1],cuts[1:])];angles.extend(mids[i] for i in np.linspace(0,len(mids)-1,min(4,len(mids))).astype(int))
  for kind,theta in [(1,t) for t in angles]+[(0,0),(2,0)]:
   g=json.loads(call(a,b,'geometry',*q,kind,theta));p=ind.rays.independent_points(a,b,q,kind,theta,n=16001)
   if not len(p):continue
   directions=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)];support=p[np.unique([int(np.argmax(p@u)) for u in directions])];low=ind.exact_finite_radius(support);up=g['radius_upper'];outside=float(np.linalg.norm(p-np.array(g['center']),axis=1).max()-up)
   z={'case':name,'w':w,'kind':kind,'theta':theta,'lower_m':low,'upper_m':up,'gap_m':up-low,'outside_m':outside};geo.append(z);assert outside<2e-5 and -2e-5<up-low<.01,z
  sim=json.loads(call(a,b,'mc',*q,20000,20261013+int(a)+int(b)+int(100*w)));sim.update(case=name,w=w,J_reference=v['J'],P_reference=v['P_finish'])
  sim['J_zscore']=(sim['J_mean']-v['J'])/sim['J_se'] if sim['J_se'] else 0;sim['P_zscore']=(sim['P_finish']-v['P_finish'])/sim['P_finish_se'] if sim['P_finish_se'] else 0
  assert sim['invalid']==0 and abs(sim['J_zscore'])<4 and abs(sim['P_zscore'])<4,sim
  sims.append(sim)
 allrows.extend(verified);(file.parent/'verified_candidates.json').write_text(json.dumps(verified,indent=2));cases.append({'case':name,'candidate_count':len(verified),'evaluations':case['evaluation_count'],'elapsed_s':case['elapsed_seconds']});print('Verified',name,flush=True)
 dump('progress',{'cases':cases,'convergence':checks,'geometry':geo,'simulations':sims,'rounding':rounding})
# Direct semantic examples distinguish the revised objective from the previous onsite-zero rule.
semantic=[]
for a,b,q in [(0,0,[700,0]),(0,0,[813,521]),(1700,0,[70,0]),(1780,0,[10,0])]:
 v=ev(a,b,q);legacy=float(call(a,b,'baseline',*q,6));strong=json.loads(call(a,b,'geometry',*q,0,0));z={'case':[a,b],'q_local':q,'J_radius':v['J'],'legacy_J':legacy,'difference':v['J']-legacy,'P_H':v['P_H'],'rho_H':strong['radius_upper'],'P_onsite':v['P_onsite']};semantic.append(z)
 assert v['J']>=legacy-1e-5
 if v['P_H']>0:assert strong['radius_upper']>0 and v['J']-legacy>=v['P_H']*strong['radius_upper']-2e-4,z
 if v['P_onsite']==0:assert abs(v['J']-legacy)<2e-5,z
 else:assert v['J']>legacy+1e-4,z
# All candidates re-evaluated under one precision; select best within the verified pool.
for a,b in sorted(set((r['a_m'],r['beta_deg']) for r in allrows)):
 pool=[r for r in allrows if r['a_m']==a and r['beta_deg']==b]
 for w in [r['w'] for r in pool]:
  r=next(z for z in pool if z['w']==w);f=lambda z:(1-w)*z['J']/20+w*(1-min(1.,max(0.,z['P_finish'])))
  assert f(r)<=min(f(z) for z in pool)+1e-7,(a,b,w)
origin=[r for r in allrows if r['a_m']==0];typical=[next(r for r in allrows if r['a_m']==a and r['beta_deg']==b and r['w']==.5) for a,b in [(0,0),(1200,30),(1200,90),(1200,150),(1700,0)]]
for name,rows in [('all_candidates',allrows),('origin_weights',origin),('typical_cases',typical)]:
 with (ROOT/f'results/{name}.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary={'status':'PASS','cases':cases,'convergence':checks,'geometry':geo,'simulations':sims,'rounding':rounding,'semantic':semantic,'max_J_refinement_m':max(abs(z['J_difference_m']) for z in checks),'max_P_refinement':max(abs(z['P_difference']) for z in checks),'max_normalization_residual':max(abs(z['probability_residual']) for z in checks),'max_geometry_gap_m':max(z['gap_m'] for z in geo),'MC_total':sum(z['n'] for z in sims),'geometry_count':len(geo),'scope':'MC independently checks conditional joint-prior integration and uses shared MEC kernel; independent rays plus support circles check geometry. Finite precision and local search do not certify continuous global optima.'}
dump('numerical_checks',summary);print({k:summary[k] for k in ['status','max_J_refinement_m','max_P_refinement','max_normalization_residual','max_geometry_gap_m','MC_total','geometry_count']})
