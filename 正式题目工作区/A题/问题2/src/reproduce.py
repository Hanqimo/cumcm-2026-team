"""Replay the selected main computation without overwriting any existing run."""
from pathlib import Path
import datetime,subprocess,sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
name='REPLAY_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
cmd=[sys.executable,str(ROOT/'src/run.py'),name,'--N','12800','--s','1024','--tol','1e-12']
subprocess.run(cmd,cwd=ROOT,check=True)
a=np.loadtxt(ROOT/'runs/R006_N12800_s1024/solution_samples.csv',delimiter=',',skiprows=1)
b=np.loadtxt(ROOT/'runs'/name/'solution_samples.csv',delimiter=',',skiprows=1)
assert a.shape==b.shape
check={'original':'R006_N12800_s1024','replay':name,'max_T_difference':float(abs(a[:,1:22]-b[:,1:22]).max()),'max_C_difference':float(abs(a[:,22:]-b[:,22:]).max())}
(ROOT/'runs'/name/'replay_comparison.json').write_text(json.dumps(check,indent=2));print(json.dumps(check))
