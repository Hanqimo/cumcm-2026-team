from pathlib import Path
import csv,importlib.util,json,math,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ind',ROOT/'src/independent_geometry.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
def call(a,b,*args):return subprocess.check_output([str(ROOT/'solver'),str(a),str(b),*map(str,args)],text=True)
def ev(a,b,q,level=6,scan=128):return {k:float(v) for k,v in next(csv.DictReader(call(a,b,'eval',*q,level,scan).splitlines())).items()}
def dump(name,obj):(ROOT/f'verification/{name}.json').write_text(json.dumps(obj,indent=2))

# Rebuild final summary from completed verification checkpoints and verified candidate files.
p=json.loads((ROOT/'verification/progress.json').read_text());checks=p['convergence'];geo=p['geometry'];sims=p['simulations'];rounding=p['rounding'];cases=p['cases'];allrows=[]
for path in sorted((ROOT/'results').glob('*/verified_candidates.json')):allrows.extend(json.loads(path.read_text()))
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
