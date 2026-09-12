"""Reproduce this minimax run without changing the preserved baseline results."""
import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def call(args,log=None):
    if log:
        with log.open('w') as f:subprocess.run(args,check=True,stdout=f,stderr=subprocess.STDOUT)
    else:subprocess.run(args,check=True)
def main():
    (ROOT/'runs/R001').mkdir(parents=True,exist_ok=True);(ROOT/'verification').mkdir(exist_ok=True)
    call(['clang++','-std=c++17','-O3',str(ROOT/'src/worst_solver.cpp'),'-o',str(ROOT/'worst_solver')])
    call(['clang++','-std=c++17','-O3',str(ROOT.parent/'src/solver.cpp'),'-o',str(ROOT/'expected_solver')])
    call([sys.executable,str(ROOT/'src/search_worst.py')],ROOT/'runs/R001/search.stdout')
    call([sys.executable,str(ROOT/'src/verify_compare.py')],ROOT/'verification/verify.stdout')
    comparison=json.loads((ROOT/'runs/R001/comparison.json').read_text())
    upper=comparison['results']['minimax']['strict_worst']['worst_upper']
    call([str(ROOT/'worst_solver'),'global',str(upper),'0.001','2000000',str(ROOT/'verification/global_bound_0001.json')],ROOT/'verification/global_bound_fine.stdout')
    bound=json.loads((ROOT/'verification/global_bound_0001.json').read_text());assert bound['completed']
    call([sys.executable,str(ROOT/'src/verify_cells_candidates.py')],ROOT/'verification/candidates.stdout')
    q=comparison['results']['minimax']['q']
    call([str(ROOT/'expected_solver'),'mc',*map(str,q),'250000','20260912'],ROOT/'verification/minimax_monte_carlo.json')
    call([sys.executable,str(ROOT/'src/manifest.py')])
    print('Completed minimax optimization, comparison, angular/global bounds and independent geometry.')
if __name__=='__main__':main()
