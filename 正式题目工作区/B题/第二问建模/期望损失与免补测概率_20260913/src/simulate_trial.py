"""Joint-prior conditional simulation; each world shares one fixed R across both observations."""
from pathlib import Path
import csv,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1]

def main():
 records=[]
 for name,weights in [('a0_b0',[0,.35,.65,1]),('a1700_b90',[0]),('a1780_b0',[0])]:
  case=json.loads((ROOT/'results'/name/'summary.json').read_text())
  for w in weights:
   r=next(r for r in case['candidates'] if r['w']==w);start=time.monotonic()
   sim=json.loads(subprocess.check_output([str(ROOT/'solver'),str(case['a']),str(case['beta_deg']),'mc',str(r['x']),str(r['y']),'60000',str(20260913+len(records))],text=True))
   sim.update(case=name,w=w,J_reference=r['J'],P_finish_reference=r['P_finish'],elapsed_seconds=time.monotonic()-start)
   sim['J_zscore']=(sim['J_mean']-r['J'])/sim['J_se'] if sim['J_se']>0 else 0
   sim['P_finish_zscore']=(sim['P_finish']-r['P_finish'])/sim['P_finish_se'] if sim['P_finish_se']>0 else 0
   records.append(sim);(ROOT/'verification/joint_prior_simulation.json').write_text(json.dumps(records,indent=2))
   print(name,w,'J_z',sim['J_zscore'],'P_z',sim['P_finish_zscore'],flush=True)

if __name__=='__main__':main()
