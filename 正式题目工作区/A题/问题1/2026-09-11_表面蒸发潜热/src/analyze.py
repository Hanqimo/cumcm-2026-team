from pathlib import Path
import json,math,csv,hashlib
import numpy as np
P=Path(__file__).resolve().parents[1]
def load(name):return np.loadtxt(P/'runs'/name/'solution_samples.csv',delimiter=',',skiprows=1)
def stat(name):return json.loads((P/'runs'/name/'solution_stats.json').read_text())
def compare(a,b,kind='T',acol=1,bcol=1):
 x,y=load(a),load(b);assert len(x)==len(y)==1801;u,v=x[1:,acol:acol+21],y[1:,bcol:bcol+21];d=abs(u-v);i,j=np.unravel_index(d.argmax(),d.shape)
 return {'coarse':a,'fine':b,'field':kind,'max_abs_difference':float(d[i,j]),'time_s':int(i+1),'radius_cm':float(j/10),'rms_difference':float(np.sqrt(np.mean(d*d))),'round4_disagreements':int(np.sum(np.round(u,4)!=np.round(v,4))),'passes_4e_6':float(d[i,j])<=4e-6}
def bj(order,x):
 x=np.asarray(x);term=np.ones_like(x,dtype=float) if order==0 else x/2;total=term.copy()
 for k in range(1,40):term=term*(-x*x/4)/(k*(k+order));total+=term
 return total
def root(bi):
 a,b=0.,2.40482555769577
 for _ in range(80):
  m=(a+b)/2
  if m*bj(1,m)-bi*bj(0,m)>0:b=m
  else:a=m
 return (a+b)/2
pairs={'thermal_time_coarse':('Ttime1024','Tfrom_CCN12800_4096'),'thermal_time_final':('Tfrom_CCN12800_4096','FINAL'),'thermal_space_final':('Tspace6400','FINAL'),'moisture_time_coarse_T':('Ctime1024','Ctime2048'),'moisture_time_final_T':('Ctime2048','FINAL'),'moisture_space_final_T':('Cspace6400','FINAL'),'moisture_time_coarse_C':('CCN12800_1024','CCN12800_2048'),'moisture_time_final_C':('CCN12800_2048','CCN12800_4096'),'moisture_space_final_C':('CCN6400_4096','CCN12800_4096'),'tight_C':('CCN12800_4096','CCN12800_4096_tight'),'tight_T':('FINAL','Ttight')}
checks={'comparisons':{},'analytic':[]}
for key,(a,b) in pairs.items():
 if (P/'runs'/a/'solution_stats.json').exists() and (P/'runs'/b/'solution_stats.json').exists():checks['comparisons'][key]=compare(a,b,'C' if key.endswith('_C') else 'T')
for prefix in ['thermal_time','moisture_time']:
 for suffix in ([''] if prefix=='thermal_time' else ['_T','_C']):
  a=checks['comparisons'].get(prefix+'_coarse'+suffix);b=checks['comparisons'].get(prefix+'_final'+suffix)
  if a and b:b['observed_order']=math.log2(a['max_abs_difference']/b['max_abs_difference'])
for group in ['CN_bessel','CCN_bessel','CCN_mms']:
 for n in [80,160,320]:
  name=f'{group}{n}';a=load(name);r=np.arange(21)[None,:]*.001;t=a[:,0,None]
  if group=='CCN_mms':exact=1+.1*np.exp(-t/100)*(1+(r/.02)**2)
  else:
   thermal=group=='CN_bessel';conductivity=.36 if thermal else 5e-9;capacity=820*2600 if thermal else 1;h=25-2370*.0002 if thermal else 8e-7;mu=root(h*.02/conductivity);base,amp=(28,5) if thermal else (1,.2);exact=base+amp*bj(0,mu*r/.02)*np.exp(-conductivity/capacity*mu*mu*t/.02**2)
  checks['analytic'].append({'case':name,'N':n,'independent_sample_max_error':float(np.max(abs(a[:,1:22]-exact))),'all_node_integer_time_error':stat(name)['exact_max_error']})
for name,value in [('CN_equilibrium',28),('CCN_equilibrium200',2.55)]:checks[name]={'max_constant_error':float(np.max(abs(load(name)[:,1:22]-value)))}
a=load('CN_zero');checks['zero_latent']={'max_difference':float(np.max(abs(a[:,1:22]-a[:,22:43])))}
checks['BE_moisture_reference']=compare('C12800_32768','CCN12800_4096','C',22,1)
checks['BE_moisture_reference_coarse']=compare('C12800_16384','CCN12800_4096','C',22,1)
if (P/'runs/CN800cross/solution_stats.json').exists():
 checks['BE_thermal_reference']=compare('T800_65536_C8192','CN800cross');checks['BE_thermal_reference_coarse']=compare('T800_32768_C8192','CN800cross')
(P/'verification/checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
