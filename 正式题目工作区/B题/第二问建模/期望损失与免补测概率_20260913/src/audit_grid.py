"""Independent 50 m spatial mesh, shifted by 25 m, reuses only the score evaluator."""
from pathlib import Path
import json,time
import numpy as np
from search_trial import ROOT,Evaluator,score

def main():
 out=ROOT/'verification/shifted_grid';out.mkdir(exist_ok=False);ev=Evaluator(0,0,out)
 rows=json.loads((ROOT/'results/a0_b0/summary.json').read_text())['candidates'];start=time.monotonic();best={r['w']:None for r in rows}
 for x in np.arange(-1475,3026,50):
  for y in np.arange(25,1576,50):
   r=ev.ev([x,y],3,12)
   if r is None:continue
   for candidate in rows:
    w=candidate['w']
    if best[w] is None or score(r,w)<score(best[w],w):best[w]=r
 ev.close()
 check=[{'w':r['w'],'saved_F':score(r,r['w']),'shifted_grid_best_F':score(best[r['w']],r['w']),'saved_advantage':score(best[r['w']],r['w'])-score(r,r['w']),'shifted_grid_best':best[r['w']]} for r in rows]
 result={'step_m':50,'offset_m':25,'evaluations':len(ev.rows),'elapsed_seconds':time.monotonic()-start,'weights':check,'no_better_grid_node':all(r['saved_advantage']>=-2e-6 for r in check),'not_a_global_optimality_proof':True}
 (ROOT/'verification/shifted_grid_audit.json').write_text(json.dumps(result,indent=2));print(result['no_better_grid_node'],result['evaluations'],result['elapsed_seconds'])

if __name__=='__main__':main()
