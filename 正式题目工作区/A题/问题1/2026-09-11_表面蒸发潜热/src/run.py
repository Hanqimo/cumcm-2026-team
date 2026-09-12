from pathlib import Path
import argparse,subprocess,json,hashlib,datetime,time,platform
P=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('kind',choices=['C','CCN','T','CN']);p.add_argument('name');p.add_argument('--n',type=int,required=True);p.add_argument('--den',type=int,required=True);p.add_argument('--history',default='');p.add_argument('--lambda_',type=float,default=1);p.add_argument('--mode',default='real');p.add_argument('--end',type=int,default=1800);p.add_argument('--tol',type=float,default=1e-12);p.add_argument('--budget',type=int,default=600);p.add_argument('--exe');a=p.parse_args()
f=P/'runs'/a.name;f.mkdir(exist_ok=False);pref=f/'solution'
exe=a.exe or '/private/tmp/q1_latent_'+('moisture' if a.kind=='C' else 'moisture_cn' if a.kind=='CCN' else 'thermal_cn' if a.kind=='CN' else 'thermal')
if a.kind=='C':args=[str(P/'inputs/environment.csv'),str(pref),str(a.n),str(1/a.den),'1',str(a.end),str(a.tol),a.mode,'50',str(a.budget)]
elif a.kind=='CCN':args=[str(P/'inputs/environment.csv'),str(pref),str(a.n),str(a.den),str(a.tol),a.mode,str(a.end),str(a.budget)]
else:args=[str(P/'inputs/environment.csv'),str(P/'runs'/a.history/'solution_surface.csv'),str(pref),str(a.n),str(a.den),str(a.lambda_),a.mode,str(a.end),str(a.budget)]
hashf=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
try: head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True,stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError: head=None
m={'config':vars(a),'command':[exe]+args,'cwd':str(P),'started':datetime.datetime.now().astimezone().isoformat(),'platform':platform.platform(),'sources':{x.name:hashf(x) for x in (P/'src').glob('*') if x.suffix in ['.cpp','.hpp']},'executable_sha256':hashf(Path(exe)),'git_head':head,'uncommitted_sources':True,'inputs':{'environment':hashf(P/'inputs/environment.csv')}}
if a.kind in ['T','CN']:m['inputs']['surface_history']=hashf(P/'runs'/a.history/'solution_surface.csv')
(f/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
t=time.monotonic()
with (f/'console.log').open('w') as out:
 try:code=subprocess.run([exe]+args,stdout=out,stderr=subprocess.STDOUT,timeout=a.budget+10).returncode
 except subprocess.TimeoutExpired:code=124
m.update(exit_code=code,seconds=time.monotonic()-t,finished=datetime.datetime.now().astimezone().isoformat());(f/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print(a.name,code,m['seconds'],flush=True);raise SystemExit(code)
