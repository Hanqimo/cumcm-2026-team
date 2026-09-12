"""Read exported OOXML independently and check every requested numeric cell."""
from pathlib import Path
import json,hashlib
import numpy as np,openpyxl
p=Path(__file__).resolve().parents[1];file=p/'results/result1.xlsx';w=openpyxl.load_workbook(file,data_only=False,read_only=False)
a=np.loadtxt(p/'results/full_precision.csv',delimiter=',',skiprows=1)
assert w.sheetnames==['温度','水分浓度'];out={}
for name,col in [('温度',1),('水分浓度',22)]:
 s=w[name];assert (s.max_row,s.max_column)==(1801,22)
 rows=list(s.values);assert rows[0][0]=='时间\\到药材中心的距离'
 assert np.array_equal(np.array(rows[0][1:]),np.arange(21)/10)
 v=np.asarray(rows[1:],dtype=float);assert np.array_equal(v[:,0],np.arange(1,1801))
 expected=np.array([[round(float(x),4) for x in row] for row in a[1:,col:col+21]])
 assert np.isfinite(v).all() and np.array_equal(v[:,1:],expected)
 assert all(s.cell(i,j).number_format=='0.0000' for i in range(2,1802) for j in range(2,23))
 out[name]={'dimensions':[1801,22],'checked_numeric_result_cells':37800,'all_values_match_rounded_csv':True,'all_output_number_formats_4dp':True,'maximum_rounding_change':float(abs(v[:,1:]-a[1:,col:col+21]).max()),'freeze_panes':s.freeze_panes}
out['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(p/'verification/workbook_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out)
