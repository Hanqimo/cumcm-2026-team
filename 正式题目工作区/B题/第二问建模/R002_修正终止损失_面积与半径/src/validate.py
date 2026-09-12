import csv,json,subprocess,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=str(ROOT/'solver')
def evaluate(q,lev=5):
 return {k:float(v) for k,v in next(csv.DictReader(subprocess.check_output([S,'eval',*map(str,q),str(lev)],text=True).splitlines())).items()}
def main():
 best={n:json.loads((ROOT/'results'/n/'best.json').read_text()) for n in ['area','radius']}
 conv=[];checks={};comparisons=[]
 for name,r in best.items():
  q=[r['x'],r['y']]
  for level in [2,3,4,5,6]:conv.append(dict(name=name,level=level,**evaluate(q,level)))
  hi=conv[-1];checks[name]={'mass_residual':hi['P_H']+hi['P_N']+hi['P_A']-1,'area_level5_to6':hi['J']-conv[-2]['J'],'radius_level5_to6':hi['E_radius_loss']-conv[-2]['E_radius_loss']}
  mirror=evaluate([q[0],-q[1]],6);checks[name]['reflection_area_difference']=mirror['J']-hi['J'];checks[name]['reflection_radius_difference']=mirror['E_radius_loss']-hi['E_radius_loss']
  comparisons.append(dict(hi))
  mc=json.loads(subprocess.check_output([S,'mc',*map(str,q),'250000',str(20260912+(name=='radius'))],text=True));(ROOT/'verification'/f'mc_{name}.json').write_text(json.dumps(mc,indent=2))
  checks[name]['mc_area_zscore']=(mc['mean_area']-hi['J'])/mc['standard_error'];checks[name]['mc_radius_zscore']=(mc['mean_radius']-hi['E_radius_loss'])/mc['radius_standard_error'];checks[name]['mc_invalid']=mc['invalid']
  print(name,checks[name],flush=True)
 for name,q in [('old_area',(932.6,590)),('rounded_area',(932.6,590.0)),('rounded_radius',(906.6,572.8)),('strong_example',(500,0)),('far_baseline',(-1500,0)),('near_first',(0.01,0)),('first_north',(0,500)),('simple',(900,600))]:
  r=evaluate(q,5);comparisons.append(dict(name=name,level=5,**r))
  if name=='strong_example':
   with (ROOT/'verification/strong_branches.csv').open('w')as f:subprocess.run([S,'branches',*map(str,q)],stdout=f,check=True)
  print('comparison',name,r,flush=True)
 for filename,a in [('convergence.csv',conv),('comparison.csv',comparisons)]:
  with (ROOT/'verification'/filename).open('w')as f:
   fields=list(dict.fromkeys(k for r in a for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(a)
 with (ROOT/'verification/selftest.txt').open('w')as f:subprocess.run([S,'selftest'],stdout=f,check=True)
 (ROOT/'verification/checks.json').write_text(json.dumps(checks,indent=2))
 assert all(abs(c['mass_residual'])<1e-7 and abs(c['area_level5_to6'])<.001 and abs(c['radius_level5_to6'])<.0001 and abs(c['mc_area_zscore'])<4 and abs(c['mc_radius_zscore'])<4 and c['mc_invalid']==0 for c in checks.values())
if __name__=='__main__':main()
