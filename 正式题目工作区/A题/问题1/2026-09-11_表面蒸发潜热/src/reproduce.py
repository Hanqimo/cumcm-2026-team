"""Re-run the selected numerical model in a new directory; no overwrite, no Git changes.
Usage: python3 src/reproduce.py /absolute/path/to/new/directory
Requires a C++17 compiler with POSIX j0/j1, Python 3 and NumPy.
"""
from pathlib import Path
import sys,shutil,tempfile,subprocess,json,hashlib
import numpy as np
root=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2:raise SystemExit(__doc__)
dest=Path(sys.argv[1]).expanduser().resolve()
if dest.exists():raise SystemExit('Destination exists. Choose a NEW directory.')
dest.mkdir(parents=True)
for name in ['inputs','src','model']:shutil.copytree(root/name,dest/name,ignore=shutil.ignore_patterns('__pycache__'))
for name in ['runs','verification','results']:(dest/name).mkdir()
with tempfile.TemporaryDirectory(prefix='q1-latent-') as build:
 b=Path(build)
 for name in ['moisture_cn','thermal_cn']:subprocess.run(['clang++','-O3','-std=c++17',str(dest/'src'/f'{name}.cpp'),'-o',str(b/name)],check=True)
 subprocess.run([sys.executable,str(dest/'src/run.py'),'CCN','CCN12800_4096','--n','12800','--den','4096','--exe',str(b/'moisture_cn')],check=True)
 subprocess.run([sys.executable,str(dest/'src/run.py'),'CN','FINAL','--n','12800','--den','4096','--history','CCN12800_4096','--exe',str(b/'thermal_cn')],check=True)
x=np.loadtxt(dest/'runs/FINAL/solution_samples.csv',delimiter=',',skiprows=1);c=np.loadtxt(dest/'runs/CCN12800_4096/solution_samples.csv',delimiter=',',skiprows=1)
a=np.column_stack([x[:,0],x[:,1:22],c[:,1:22]]);np.savetxt(dest/'results/full_precision.csv',a,delimiter=',',header=','.join(['time_s']+[f'{v}_r{j/10:.1f}cm' for v in ['T','C'] for j in range(21)]),comments='',fmt='%.17g')
reference=np.loadtxt(root/'results/full_precision.csv',delimiter=',',skiprows=1)
check={'max_difference_to_retained_run':float(np.max(abs(reference-a))),'scope':'Selected numerical runs only. Full original verification cases and workbook export are retained in original directory.'}
(dest/'verification/reproduction_check.json').write_text(json.dumps(check,indent=2));print(check)
