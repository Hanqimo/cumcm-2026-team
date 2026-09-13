from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,sys,json,time
ROOT=Path(__file__).resolve().parents[1]
def one(case):
 a,b=case;name=f'a{a}_b{b}';t=time.monotonic()
 with (ROOT/f'verification/search_{name}.log').open('w') as f:
  p=subprocess.run([sys.executable,str(ROOT/'src/search.py'),'--a',str(a),'--beta',str(b)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 if p.returncode:raise RuntimeError(f'{name}: exit {p.returncode}')
 return {'case':name,'elapsed_s':time.monotonic()-t,'exit_code':p.returncode}
if __name__=='__main__':
 reports=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for future in as_completed([pool.submit(one,c) for c in [(0,0),(1200,30),(1200,90),(1200,150),(1700,0),(1700,90),(1780,0)]]):
   r=future.result();reports.append(r);print(r,flush=True);(ROOT/'verification/run_times.json').write_text(json.dumps(reports,indent=2))
