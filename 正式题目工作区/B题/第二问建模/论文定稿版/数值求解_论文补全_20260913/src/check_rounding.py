from pathlib import Path
import json,csv,subprocess
ROOT=Path(__file__).resolve().parents[1];rows=list(csv.DictReader((ROOT/'results/origin_weights.csv').open()));checks=[]
for row in rows:
 q=[round(float(row['q_x_m']),1),round(float(row['q_abs_y_m']),1)]
 text=subprocess.check_output([str(ROOT/'solver'),'0','0','eval',*map(str,q),'6','128'],text=True);v={k:float(z) for k,z in next(csv.DictReader(text.splitlines())).items()}
 rec={'w':float(row['w']),'q_rounded':q,'J_change_m':v['J']-float(row['J_m']),'P_change':v['P_finish']-float(row['P_finish'])};checks.append(rec)
 assert abs(rec['J_change_m'])<.005 and abs(rec['P_change'])<.00005,rec
(ROOT/'verification/origin_rounding.json').write_text(json.dumps(checks,indent=2));print('Origin table rounding passed',len(checks))
