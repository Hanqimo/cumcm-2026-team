"""Record current final-model files without dependencies on obsolete directories."""
from pathlib import Path
import json,datetime,platform,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 repo=next(p for p in ROOT.parents if (p/'.git').exists())
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 files=[p for folder in ['src','results','verification'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix in ['.py','.cpp','.json','.csv']]
 files += [p for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.md','.tex','.pdf']]
 gitstatus=subprocess.check_output(['git','status','--porcelain','--',str(ROOT)],cwd=repo,text=True)
 data={'model':'Q2-expected-M01-v03-a-beta','status':'single-current-working-model','model_scope':'S1=(a,0), first bearing beta, C1(a,beta)>0','computed_scope':{'a_m':0,'beta_rad':0},'solver_scope':'baseline-only; general parameter optimization not implemented','updated_at':datetime.datetime.now().astimezone().isoformat(),'source_model':'第二问模型.tex','model_sha256':h(ROOT/'第二问模型.tex'),'working_directory':str(ROOT),'git_head_at_record':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'git_branch':subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip(),'uncommitted_work':bool(gitstatus),'git_note':'Source hashes identify the consolidated working version. No automatic commit or push.','python_executable':sys.executable,'python_version':sys.version,'platform':platform.platform(),'compiler':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0],'compile_command':'clang++ -std=c++17 -O3 src/solver.cpp -o solver','reproduce_command':f'{sys.executable} src/reproduce.py','pdf_compile_command':'latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build 第二问模型.tex','original_computation_provenance':json.loads((ROOT/'verification/计算来源.json').read_text()),'search_record':json.loads((ROOT/'results/search_summary.json').read_text()),'random_seeds':[20260912,20260913,1729],'validation_status':'Existing convergence, geometry and simulation checks apply only to a=0,beta=0. General-model algebraic checks recorded separately; no general-parameter numerical optimization performed. Baseline continuous global optimum not certified.','deferred':['clearance-success probability and improvements','general a,beta numerical solution (baseline worst-case work is in worstcase/)' ,'distribution sensitivity and robustness'],'sha256':{str(p.relative_to(ROOT)):h(p) for p in files}}
 (ROOT/'manifest.yaml').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print('manifest.yaml written')
if __name__=='__main__':main()
