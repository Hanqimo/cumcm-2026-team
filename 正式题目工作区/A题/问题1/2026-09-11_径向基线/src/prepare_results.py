"""Select each decoupled field from its verified run; no extrapolation or clipping."""
from pathlib import Path
import json,hashlib,csv,gzip
import numpy as np,openpyxl
from verify import load
p=Path(__file__).resolve().parents[1]
checks=json.loads((p/'verification/checks.json').read_text())
for f in ['T','C']:
 for direction in ['time','space']:assert checks['comparisons'][f'{f}_{direction}_final_{f}']['passes_4e_6']
assert checks['tightening']['passes_1e_7']
selected={'T':'R_N1600_s131072','C':'R_N12800_s8192'}
T=load(selected['T']);C=load(selected['C']);a=np.column_stack([T[:,0],T[:,1:22],C[:,22:43]])
assert a.shape==(1801,43) and np.isfinite(a).all()
header=','.join(['time_s']+[f'{f}_r{j/10:.1f}cm' for f in ['T','C'] for j in range(21)])
np.savetxt(p/'results/full_precision.csv',a,delimiter=',',header=header,comments='',fmt='%.17g')
np.savetxt(p/'results/paper_table_temperature.csv',a[np.array([100,300,600,900,1200,1500,1800])][:,[0,1,6,11,16,21]],delimiter=',',header='time_s,r0cm,r0.5cm,r1cm,r1.5cm,r2cm',comments='',fmt=['%d']+['%.4f']*5)
np.savetxt(p/'results/paper_table_moisture.csv',a[np.array([100,300,600,900,1200,1500,1800])][:,[0,22,27,32,37,42]],delimiter=',',header='time_s,r0cm,r0.5cm,r1cm,r1.5cm,r2cm',comments='',fmt=['%d']+['%.4f']*5)
rounding=[]
for f,col in [('T',1),('C',22)]:
 for dim in ['time','space']:
  x=checks['comparisons'][f'{f}_{dim}_final_{f}'];coarse=load(x['coarse'])[1:,col:col+21];fine=load(x['fine'])[1:,col:col+21]
  for i,j in np.argwhere(np.round(coarse,4)!=np.round(fine,4)):
   rounding.append([f,dim,int(i+1),j/10,float(coarse[i,j]),float(fine[i,j]),f'{coarse[i,j]:.4f}',f'{fine[i,j]:.4f}'])
with (p/'verification/rounding_disagreements.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['field','refinement','time_s','radius_cm','coarse_raw','fine_raw','coarse_4dp','fine_4dp']);w.writerows(rounding)
# Expand the template ellipses; preserve its actual first-cell wording and worksheet names.
wb=openpyxl.load_workbook(p/'inputs/result1_template.xlsx',read_only=True,data_only=True)
payload={name:[[wb[name]['A1'].value]+[j/10 for j in range(21)]]+[[int(row[0])]+[round(float(x),4) for x in row[col:col+21]] for row in a[1:]] for name,col in [('温度',1),('水分浓度',22)]}
(p/'results/workbook_payload.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
meta={'model':'M01-v01','algorithm':'node-centred FV + backward Euler + Picard, arithmetic face D','implementation':'A01-run-20260911; independent field resolutions and prescribed piecewise time steps','selected_runs':selected,'output_shape_per_field':[1800,21],'first_output_s':1,'last_output_s':1800,'radius_cm':[j/10 for j in range(21)],'xlsx_values':'Rounded to 4 decimals only at export. Authoritative unrounded values are full_precision.csv.','rounding_warning':'Differences at the fourth decimal remain near rounding boundaries; see verification/rounding_disagreements.csv. No claim that all four-decimal values are invariant.','acceptance':'Full-output empirical grid/time refinement differences below 4e-6, nonlinear tightening below 1e-7; not a rigorous continuum error bound or physical-model validation.','sources':{}}
for field,name in selected.items():
 folder=p/'runs'/name;s=json.loads((folder/'solution_stats.json').read_text());assert s['completed'] and s['rejected_steps']==0
 state=np.loadtxt(folder/'solution_final_state.csv',delimiter=',',skiprows=1);r=state[:,1];faces=np.r_[0,(r[:-1]+r[1:])/2,.02];w=np.diff(faces**2)/2;values=state[:,2 if field=='T' else 3]
 meta['sources'][field]={'run':name,'N':s['N'],'base_dt':s['base_dt'],'steps':s['steps'],'stats':s,'weighted_mean_at_1800':float(np.sum(w*values)/(.02**2/2)),'center_at_1800':float(values[0]),'surface_at_1800':float(values[-1]),'samples_sha256':hashlib.sha256((folder/'solution_samples.csv').read_bytes()).hexdigest()}
 # Exact deterministic accepted time grid, reconstructed only after checking zero rejections.
 t=0.;steps=0
 with gzip.open(p/'verification'/f'accepted_time_grid_{field}.csv.gz','wt') as f:
  f.write('step,time_old_s,dt_s,time_new_s\n')
  while t<1800:
   m=1 if t<2 else 4 if t<8 else 16 if t<32 else 64 if t<128 else 128 if t<512 else 256
   dt=min(s['base_dt']*m,1800-t,np.floor(t+1e-10)+1-t);steps+=1
   f.write(f'{steps},{t:.17g},{dt:.17g},{t+dt:.17g}\n');t+=dt
 assert steps==s['steps']
meta['moisture_mean_fraction_lost']=(2.55-meta['sources']['C']['weighted_mean_at_1800'])/2.55
(p/'results/selection.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(meta,ensure_ascii=False,indent=2))
