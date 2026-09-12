from pathlib import Path
import json,hashlib
import numpy as np,openpyxl
P=Path(__file__).resolve().parents[1]
p=json.loads((P/'results/workbook_payload.json').read_text());out={}
w=openpyxl.load_workbook(P/'results/result1.xlsx',data_only=True);assert w.sheetnames==['温度','水分浓度']
for name in w.sheetnames:
 s=w[name];assert (s.max_row,s.max_column)==(1801,22);a=np.array(list(s.values)[1:],float);b=np.array(p[name][1:],float);assert np.array_equal(a,b);assert all(s.cell(i,j).number_format=='0.0000' for i in range(2,1802) for j in range(2,23));out[name]={'result_values_checked':37800,'all_equal_to_rounded_raw':True,'four_decimal_formats':True}
c=openpyxl.load_workbook(P/'results/模型对比.xlsx',data_only=True);cf=openpyxl.load_workbook(P/'results/模型对比.xlsx',data_only=False);assert c.sheetnames==['对比概览','时间序列'];a=np.array(list(c['时间序列'].iter_rows(min_row=2,max_row=1802,min_col=1,max_col=13,values_only=True)),float);b=np.array(p['comparison_series'][1:],float);assert np.max(abs(a-b))<1e-10
s=c['对比概览'];m=p['metadata'];assert abs(s['D6'].value-m['drop_at1800'][0])<1e-10;assert abs(s['D7'].value-m['drop_at1800'][4])<1e-10;assert abs(s['D8'].value-m['mean_drop_at1800'])<1e-10
assert len(cf['对比概览']._charts)==1
out['comparison']={'time_series_values_checked':int(a.size),'formula_caches_match_raw':True,'summary_matches_raw':True,'chart_count':1}
out['files']={name:hashlib.sha256((P/'results'/name).read_bytes()).hexdigest() for name in ['result1.xlsx','模型对比.xlsx']}
(P/'verification/workbook_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out)
