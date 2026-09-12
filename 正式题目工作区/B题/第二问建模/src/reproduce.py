"""Recompute both objectives and verification; Python 3 + NumPy + C++17 required."""
from pathlib import Path
import subprocess,sys,time,os
ROOT=Path(__file__).resolve().parents[1]
def main():
 os.chdir(ROOT);deadline=time.monotonic()+900
 def run(args,output):
  with open(output,'w')as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=max(1,deadline-time.monotonic()))
 run(['clang++','-std=c++17','-O3','src/solver.cpp','-o','solver'],'verification/compile.log')
 run([sys.executable,'src/search.py'],'results/search.log')
 run([sys.executable,'-c',"import sys;sys.path.insert(0,'src');from search import batch;batch('nearopt5',[(x,y) for x in range(800,1051,5) for y in range(450,751,5)],3)"],'results/nearopt.log')
 run([sys.executable,'src/validate.py'],'verification/validate.log')
 run([sys.executable,'src/verify_geometry.py'],'verification/geometry_summary.json')
 run([sys.executable,'src/summarize.py'],'results/summary.stdout')
 run([sys.executable,'src/manifest.py'],'verification/manifest.log')
 print('Completed. See 结果汇报.md and results/{area,radius}/result.json.')
if __name__=='__main__':main()
