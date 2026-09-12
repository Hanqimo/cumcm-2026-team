"""Re-read immutable source snapshots and check extraction without modifying originals."""
from pathlib import Path
import hashlib,json
import numpy as np,openpyxl
p=Path(__file__).resolve().parents[1]
m=json.loads((p/'inputs/manifest.json').read_text());records=[]
for x in m['files']:
 h=hashlib.sha256((p/x['snapshot']).read_bytes()).hexdigest();assert h==x['sha256'];records.append({'file':x['snapshot'],'sha256_matches':True})
w=openpyxl.load_workbook(p/'inputs/附件1.xlsx',read_only=True,data_only=True)
a=np.asarray(list(w.active.values)[1:],dtype=float)
b=np.loadtxt(p/'inputs/environment.csv',delimiter=',',skiprows=1)
assert a.shape==(241,3) and np.array_equal(a,b) and np.isfinite(a).all()
assert np.array_equal(a[:,0],np.arange(0,14401,60)) and a[0,0]==0 and a[-1,0]>=1800 and np.all(a[:,2]>0)
t=openpyxl.load_workbook(p/'inputs/result1_template.xlsx',read_only=True,data_only=True)
assert t.sheetnames==['温度','水分浓度']
out={'files':records,'extracted_values_exactly_equal':True,'rows':len(a),'columns':['time_s','air_temperature_C','effective_equilibrium_moisture_kg_kg'],'used_time_range_s':[0,1800],'first_row':a[0].tolist(),'row_1800':a[30].tolist(),'template_sheet_names':t.sheetnames,'template_policy':'Expand ellipsis to 1800 integer seconds and 21 radial positions; keep A1 wording and sheet names.'}
(p/'verification/input_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out)
