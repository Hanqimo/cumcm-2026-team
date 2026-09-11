from pathlib import Path
import json,csv,hashlib
import numpy as np,openpyxl
from analyze import compare
P=Path(__file__).resolve().parents[1]
x=np.loadtxt(P/'runs/FINAL/solution_samples.csv',delimiter=',',skiprows=1);c=np.loadtxt(P/'runs/CCN12800_4096/solution_samples.csv',delimiter=',',skiprows=1);old=np.loadtxt(P/'inputs/baseline_full_precision.csv',delimiter=',',skiprows=1);dg=np.loadtxt(P/'runs/FINAL/solution_diagnostics.csv',delimiter=',',skiprows=1)
v=json.loads((P/'verification/checks.json').read_text());assert len(v['comparisons'])==11
assert all(z['passes_4e_6'] for z in v['comparisons'].values())
t=x[:,0];T=x[:,1:22];T0=x[:,22:43];C=c[:,1:22];delta=T0-T
assert np.array_equal(t,np.arange(1801)) and c.shape==(1801,22)
full=np.column_stack([t,T,C]);header=','.join(['time_s']+[f'{field}_r{j/10:.1f}cm' for field in ['T','C'] for j in range(21)])
np.savetxt(P/'results/full_precision.csv',full,delimiter=',',header=header,comments='',fmt='%.17g')
with (P/'results/comparison_full.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['time_s','radius_cm','T_no_latent_C','T_latent_C','temperature_drop_C','C_shared_kg_kg','historical_T_C','historical_C_kg_kg'])
 for i in range(1801):
  for j in range(21):w.writerow([i,j/10,T0[i,j],T[i,j],delta[i,j],C[i,j],old[i,1+j],old[i,22+j]])
indices=np.unravel_index(delta[1:].argmax(),delta[1:].shape);Tstats=json.loads((P/'runs/FINAL/solution_stats.json').read_text());Cstats=json.loads((P/'runs/CCN12800_4096/solution_stats.json').read_text())
props=np.loadtxt(P/'inputs/water_properties.csv',delimiter=',',skiprows=1);env=np.loadtxt(P/'inputs/environment.csv',delimiter=',',skiprows=1);airw=np.interp(t,env[:,0],env[:,2]);pv=101325*airw/(.62198+airw);dew=np.interp(np.log(pv),np.log(props[:,2]),props[:,0]);low=T[:,-1]<dew
rhoD=820/3.55;geom=2*np.pi*.25
cf=np.loadtxt(P/'runs/CCN12800_4096/solution_final.csv',delimiter=',',skiprows=1);faces=np.r_[0,(cf[:-1,0]+cf[1:,0])/2,.02];weights=np.diff(faces**2)/2;meanC=float(np.sum(weights*cf[:,1])/(.02**2/2));waterLoss=rhoD*np.pi*.02**2*.25*(2.55-meanC)
metadata={'model':'M02-v01','algorithm':'A02 FV + Rannacher startup + Crank-Nicolson + moisture Picard','temperature_run':'FINAL','moisture_run':'CCN12800_4096','rho_d_kg_m3':rhoD,'latent_formula_J_kg':'2500900-2370*T_C','T_at1800':[float(y) for y in T[-1,[0,5,10,15,20]]],'T_no_latent_at1800':[float(y) for y in T0[-1,[0,5,10,15,20]]],'drop_at1800':[float(y) for y in delta[-1,[0,5,10,15,20]]],'C_at1800':[float(y) for y in C[-1,[0,5,10,15,20]]],'max_temperature_drop_C':float(delta[1:].max()),'max_drop_time_s':int(indices[0]+1),'max_drop_radius_cm':float(indices[1]/10),'rms_temperature_drop_C':float(np.sqrt(np.mean(delta[1:]**2))),'mean_T_at1800':float(dg[-1,5]),'mean_T0_at1800':float(dg[-1,6]),'mean_drop_at1800':float(dg[-1,6]-dg[-1,5]),'mean_C_at1800':meanC,'water_loss_kg':waterLoss,'energy_convective_J':float(dg[-1,7]),'energy_latent_J':float(dg[-1,8]),'energy_balance_J':float(dg[-1,9]),'intergrid_water_transfer_defect_kg':float(Tstats['integral_water_per_2piL']*geom-waterLoss),'latent_flux_at1800_W_m2':float(dg[-1,3]),'convective_flux_at1800_W_m2':float(dg[-1,4]),'historical_temperature_output_max_difference_to_new_no_latent':float(abs(T0-old[:,1:22]).max()),'historical_moisture_output_max_difference':float(abs(C-old[:,22:43]).max()),'paired_model_moisture_difference':0.,'temperature_stats':Tstats,'moisture_stats':Cstats,'dewpoint_check':{'conditional_assumptions':'101325 Pa; attachment air concentration interpreted as kg vapor/kg dry air; liquid water surface has activity <= 1','interpolation':'log saturation pressure interpolated from NIST table nodes','dewpoint_initial_C':float(dew[0]),'dewpoint_at1800_C':float(dew[-1]),'first_below_dewpoint_integer_second':int(t[low][0]),'count_integer_seconds_below_dewpoint':int(low[1:].sum()),'conclusion':'If these conventional air-humidity definitions apply, continuing positive evaporation below dewpoint is inconsistent with vapor-pressure-driven mass transfer. This is a conditional sensitivity model, not a validated physical forecast.'}}
metadata['latent_flux_using_no_latent_surface_at1800_W_m2']=float((2500900-2370*T0[-1,-1])*dg[-1,1]);metadata['convection_no_latent_at1800_W_m2']=float(25*(np.interp(1800,env[:,0],env[:,1])-T0[-1,-1]))
(P/'results/selection_and_comparison.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
# Exact output workbook template (expand ellipses); raw values remain separate.
wb=openpyxl.load_workbook(P/'inputs/result1_template.xlsx',read_only=True)
payload={name:[[wb[name]['A1'].value]+[j/10 for j in range(21)]]+[[int(t[i])]+[round(float(z),4) for z in a[i]] for i in range(1,1801)] for name,a in [('温度',T),('水分浓度',C)]}
series=[['时间/s','无潜热轴心/°C','有潜热轴心/°C','无潜热表面/°C','有潜热表面/°C','表面降温/°C','无潜热均温/°C','有潜热均温/°C','平均降温/°C','共用表面含水率/(kg/kg)','蒸发水通量/(kg/m²/s)','汽化耗热/(W/m²)','条件性露点/°C']]
for i in range(1801):series.append([i,float(T0[i,0]),float(T[i,0]),float(T0[i,-1]),float(T[i,-1]),float(delta[i,-1]),float(dg[i,6]),float(dg[i,5]),float(dg[i,6]-dg[i,5]),float(C[i,-1]),float(dg[i,1]),float(dg[i,3]),float(dew[i])])
payload['comparison_series']=series;payload['metadata']=metadata
(P/'results/workbook_payload.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
# Representative tables, all sourced from the same selected full-precision fields.
with (P/'results/paper_tables.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['time_s','radius_cm','T_no_latent_C','T_latent_C','drop_C','C_kg_kg'])
 for i in [100,300,600,900,1200,1500,1800]:
  for j in [0,5,10,15,20]:w.writerow([i,j/10]+[f'{z:.4f}' for z in [T0[i,j],T[i,j],delta[i,j],C[i,j]]])
with (P/'verification/rounding_disagreements.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['check','time_s','radius_cm','coarse','fine'])
 for key,z in v['comparisons'].items():
  a=np.loadtxt(P/'runs'/z['coarse']/'solution_samples.csv',delimiter=',',skiprows=1)[1:,1:22];b=np.loadtxt(P/'runs'/z['fine']/'solution_samples.csv',delimiter=',',skiprows=1)[1:,1:22]
  for i,j in np.argwhere(np.round(a,4)!=np.round(b,4)):w.writerow([key,int(i+1),j/10,a[i,j],b[i,j]])
print(json.dumps(metadata,ensure_ascii=False,indent=2))
