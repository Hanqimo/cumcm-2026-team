"""Compile and run a uniquely identified Q2 case, with immutable input/source evidence."""
from pathlib import Path
import argparse, hashlib, json, platform, shutil, subprocess, sys, time, datetime
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument('name');a.add_argument('--N',type=int,default=400);a.add_argument('--s',type=int,default=256);a.add_argument('--tol',type=float,default=1e-12);a.add_argument('--mode',default='real',choices=['real','equilibrium','bessel','mms']);a.add_argument('--end',type=float,default=10800);a.add_argument('--budget',type=float,default=600);a.add_argument('--method',default='midpoint',choices=['midpoint','be']);a.add_argument('--schedule',type=int,default=1);o=a.parse_args()
    dest=ROOT/'runs'/o.name;dest.mkdir(exist_ok=False);source=ROOT/'src/solver.cpp';shutil.copy2(source,dest/'solver_snapshot.cpp')
    cmd=['clang++','-O3','-std=c++17',str(dest/'solver_snapshot.cpp'),'-o',str(dest/'solver')];subprocess.run(cmd,check=True,capture_output=True)
    args=[str(dest/'solver'),str(ROOT/'inputs/environment.csv'),str(dest/'solution'),str(o.N),str(o.s),str(o.tol),o.mode,str(o.end),str(o.budget),o.method,str(o.schedule)]
    now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest={'model':'Q2-M01-v01','algorithm':'A01-FV-implicit-midpoint-coupled-Picard','data':'D01','config':vars(o),'source_sha256':digest(source),'environment_sha256':digest(ROOT/'inputs/environment.csv'),'compile_command':cmd,'command':args,'cwd':str(ROOT),'python':sys.version,'platform':platform.platform(),'random_seed':None,'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'git_status':subprocess.check_output(['git','status','--short'],cwd=REPO,text=True),'code_uncommitted':True,'started_utc':now(),'validation_status':'pending'}
    (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    st=time.monotonic()
    with (dest/'console.log').open('w') as f:
        try:r=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=o.budget+30);code=r.returncode
        except subprocess.TimeoutExpired:code=124
    manifest.update(finished_utc=now(),wall_seconds=time.monotonic()-st,returncode=code)
    for p in sorted(dest.glob('solution*')):manifest.setdefault('outputs_sha256',{})[p.name]=digest(p)
    (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps({'run':o.name,'returncode':code,'wall_seconds':manifest['wall_seconds'],'stats':json.loads((dest/'solution_stats.json').read_text()) if (dest/'solution_stats.json').exists() else (dest/'console.log').read_text()},ensure_ascii=False))
    sys.exit(code)
if __name__=='__main__':main()
