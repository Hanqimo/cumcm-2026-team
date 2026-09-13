from pathlib import Path
import json,subprocess,numpy as np,math
ROOT=Path(__file__).resolve().parents[1]
binary=ROOT/'src/base_solver';subprocess.run(['clang++','-O3','-std=c++17',str(ROOT/'inputs/base_solver.cpp'),'-o',str(binary)],check=True)
params=json.loads((ROOT/'data/general_posterior_parameters.json').read_text());records=[]
for b in params['beta_deg']:
 info=json.loads(subprocess.check_output([str(binary),'1200',str(b),'info'],text=True));expected=params['C1_m2'][str(b)]
 assert abs(info['C1']-expected)<1e-6
 arr=np.load(ROOT/f'data/posterior_beta_{int(b)}.npz');r=arr['distance_m'];angle=arr['relative_angle_deg'];den=arr['density_per_m2'];x=1200+r[None,:]*np.cos(np.deg2rad(b+angle[:,None]));y=r[None,:]*np.sin(np.deg2rad(b+angle[:,None]))
 assert np.all(den[x*x+y*y>1800**2+1e-8]==0)
 assert np.all(den[abs(angle)>1]==0) and np.max(den)<14e-5
 records.append({'a_m':1200,'beta_deg':b,'C1_radial_antiderivative_m2':expected,'C1_geometric_kernel_m2':info['C1'],'difference_m2':info['C1']-expected,'max_density_per_m2':float(den.max()),'outside_disk_density_zero':True,'outside_bearing_interval_density_zero':True})
# The two split panels retain byte-identical source data, no new optimization.
old=ROOT.parent/'论文插图_20260913'
assert all((ROOT/'data'/n).read_bytes()==(old/'data'/n).read_bytes() for n in ['feedback_profile.csv','geometry_270.json','geometry_300.json'])
(ROOT/'verification/numerical_checks.json').write_text(json.dumps({'posterior_cases':records,'feedback_source_data_unchanged':True,'new_optimization':False},indent=2))
print(json.dumps(records,indent=2))
