"""Reproduce saved results; --full also recalculates every stored optimization grid.
Core needs Python 3 + a C++17 compiler. Geometry checks additionally need NumPy.
Run from anywhere: python3 src/reproduce.py [--full]
"""
import argparse,csv,json,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args,out=None):
 if out:
  with open(out,'w')as f:subprocess.run(args,stdout=f,check=True)
 else:subprocess.run(args,check=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');opts=ap.parse_args();os.chdir(ROOT)
 run(['clang++','-std=c++17','-O3','src/solver.cpp','-o','solver'])
 if opts.full:
  for prior in [-1,1]:
   run(['./solver','batch','results/global50_input.csv',f'results/prior_{prior}_global.csv','2',str(prior)])
  levels={'coarse':1,'global50':2,'refine10':2,'refine2':3,'refine05':4,'refine01':4,'nearopt5':2,'safe_boundary':3,'safe_fine':4,'safe_interior':3,'nearopt_edge':5}
  for path in sorted(Path('results').glob('*_input.csv')):
   name=path.stem.removesuffix('_input');prior=0
   if name=='comparison':continue
   if name.startswith('prior_'):
    prior=int(name.split('_')[1]);level={'global':2,'local':3,'fine':4}[name.split('_')[-1]]
   else:level=levels.get(name,3)
   run(['./solver','batch',str(path),'results/'+name+'.csv',str(level),str(prior)])
  run(['./solver','batch','results/nearopt5_input.csv','results/nearopt_high.csv','3'])
  a=list(csv.DictReader(open('results/nearopt_high.csv')));updates={(r['x'],r['y']):r for r in csv.DictReader(open('results/nearopt_edge.csv'))}
  for r in a:r.update(updates.get((r['x'],r['y']),{}))
  for name,pct in [('nearopt_final',None),('candidates_1pct',1),('candidates_5pct',5)]:
   with open('results/'+name+'.csv','w')as f:
    w=csv.DictWriter(f,fieldnames=list(a[0]));w.writeheader();w.writerows(a if pct is None else [r for r in a if float(r['J'])<=2103.78340332469*(1+pct/100)])
  for prior in [-1,1]:
   a=list(csv.DictReader(open(f'results/prior_{prior}_fine.csv')));Path(f'results/prior_{prior}_best.json').write_text(json.dumps(min(a,key=lambda r:float(r['J'])),indent=2))
 run(['./solver','batch','results/comparison_input.csv','results/comparison.csv','5'])
 conv=[]
 for level in [2,3,4,5]:
  r=next(csv.DictReader(subprocess.check_output(['./solver','eval','932.6','590',str(level)],text=True).splitlines()));r['level']=level;conv.append(r)
 with open('verification/convergence.csv','w')as f:w=csv.DictWriter(f,fieldnames=list(conv[0]));w.writeheader();w.writerows(conv)
 run(['./solver','branches','932.6','590'],'results/branches_main.csv')
 run(['./solver','selftest'],'verification/selftest.txt')
 run(['./solver','mc','932.6','590','500000','912732'],'verification/mc_main_final.json')
 run(['./solver','mc','864.316399410232','511.3558109716','500000','912731'],'verification/mc_safe.json')
 fixed=[]
 for prior in [-1,1]:
  r=next(csv.DictReader(subprocess.check_output(['./solver','eval','932.6','590','5',str(prior)],text=True).splitlines()));r['prior']=prior;fixed.append(r)
 with open('results/sensitivity_fixed.csv','w')as f:w=csv.DictWriter(f,fieldnames=list(fixed[0]));w.writeheader();w.writerows(fixed)
 run([sys.executable,'src/verify_geometry.py'],'verification/geometry_summary.json')
 run([sys.executable,'src/summarize.py'],'results/summary.stdout')
 print('Completed. See results/summary.json and verification/checks.json.')
if __name__=='__main__':main()
