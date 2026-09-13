"""Reproduce into a new directory; never overwrites the saved experiment."""
from pathlib import Path
import argparse,datetime,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--skip-figures',action='store_true');args=parser.parse_args()
 dest=args.output or ROOT/'复现'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 dest.mkdir(parents=True,exist_ok=False)
 for name in ['src','inputs']:shutil.copytree(ROOT/name,dest/name,ignore=shutil.ignore_patterns('__pycache__'))
 for name in ['results','verification','figures']:(dest/name).mkdir()
 subprocess.run(['clang++','-std=c++17','-O3',str(dest/'src/trial_solver.cpp'),'-o',str(dest/'solver')],check=True)
 for a,b in [(0,0),(1700,90),(1700,0),(1780,0)]:subprocess.run([sys.executable,str(dest/'src/search_trial.py'),'--a',str(a),'--beta',str(b)],check=True)
 for name in ['simulate_trial.py','validate_trial.py','audit_grid.py']:
  subprocess.run([sys.executable,str(dest/'src'/name)],check=True)
 if not args.skip_figures:subprocess.run([sys.executable,str(dest/'src/report_trial.py')],check=True)
 print(dest)
if __name__=='__main__':main()
