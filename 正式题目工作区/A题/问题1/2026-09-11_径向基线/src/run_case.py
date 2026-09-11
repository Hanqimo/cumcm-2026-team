"""Run one immutable configuration and retain the command, source hashes and diagnostics."""
from pathlib import Path
import argparse,datetime,hashlib,json,platform,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument("name");p.add_argument("--n",type=int,default=200)
p.add_argument("--dt",type=float,default=.25);p.add_argument("--schedule",type=int,default=0)
p.add_argument("--end",type=int,default=1800);p.add_argument("--tol",type=float,default=1e-12)
p.add_argument("--mode",default="real");p.add_argument("--maxit",type=int,default=50)
p.add_argument("--budget",type=int,default=600);p.add_argument("--exe",default="/private/tmp/a_q1_solver")
a=p.parse_args();folder=ROOT/("runs" if a.mode=="real" else "verification")/a.name
folder.mkdir(exist_ok=False)
prefix=folder/"solution"
cmd=[a.exe,str(ROOT/"inputs/environment.csv"),str(prefix),str(a.n),str(a.dt),str(a.schedule),str(a.end),str(a.tol),a.mode,str(a.maxit),str(a.budget)]
hashfile=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
try: git_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError: git_head=None
meta={"config":vars(a),"command":cmd,"started":datetime.datetime.now().astimezone().isoformat(),
      "platform":platform.platform(),"source_sha256":hashfile(ROOT/"src/solver.cpp"),
      "executable_sha256":hashfile(Path(a.exe)),"environment_sha256":hashfile(ROOT/"inputs/environment.csv"),
      "git_head":git_head,
      "uncommitted_sources":True}
(folder/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
start=time.monotonic()
with (folder/"console.log").open("w") as f:
 try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=a.budget+10);code=r.returncode
 except subprocess.TimeoutExpired:code=124
meta.update(exit_code=code,elapsed=time.monotonic()-start,finished=datetime.datetime.now().astimezone().isoformat())
(folder/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
print(json.dumps({"name":a.name,"code":code,"seconds":meta["elapsed"]}),flush=True)
raise SystemExit(code)

