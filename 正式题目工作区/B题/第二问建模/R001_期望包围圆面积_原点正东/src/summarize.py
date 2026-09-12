"""Summarize numerical outputs and assert independent numerical checks."""
import csv,json,math,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(name):return [{k:float(v)for k,v in z.items()}for z in csv.DictReader((ROOT/name).open())]
def main():
 comparison=rows('results/comparison.csv');best=comparison[0];safe=comparison[2]
 conv=rows('verification/convergence.csv');geom=json.loads((ROOT/'verification/geometry_summary.json').read_text());mc=json.loads((ROOT/'verification/mc_main_final.json').read_text());mcs=json.loads((ROOT/'verification/mc_safe.json').read_text())
 z=math.pi/180*((1000**2+1000*1500+1500**2)/3-25)
 cc=1505/(2*math.cos(math.pi/180));rr=math.sqrt(cc*cc-1505*5+25)
 test=(ROOT/'verification/selftest.txt').read_text();zc=float(re.search(r'Z=([0-9.eE+-]+)',test)[1]);rc=float(re.search(r'radius=([0-9.eE+-]+)',test)[1]);assert abs(z-zc)<1e-8 and abs(rr-rc)<1e-7
 checks={'normalizer_error':abs(z-zc),'first_MEC_analytic_error':abs(rr-rc),'normalizer_analytic':z,'first_MEC_radius_analytic':rr,'reflection_area_difference':abs(best['J']-comparison[1]['J']),'probability_residual_main':abs(best['P_H']+best['P_N']+best['P_A']-1),'convergence_level4_5_area_difference':abs(conv[-1]['J']-conv[-2]['J']),'mc_area_z_score':(mc['mean_area']-best['J'])/mc['standard_error'],'mc_safe_area_z_score':(mcs['mean_area']-safe['J'])/mcs['standard_error'],'mc_P20_z_score':(mc['P20']-best['P20'])/math.sqrt(best['P20']*(1-best['P20'])/mc['n']),'mc_invalid':mc['invalid'],'independent_geometry':geom}
 assert checks['reflection_area_difference']<1e-6
 assert checks['probability_residual_main']<1e-8
 assert checks['convergence_level4_5_area_difference']<1e-4
 assert abs(checks['mc_area_z_score'])<3 and abs(checks['mc_safe_area_z_score'])<3
 assert checks['mc_invalid']==0 and geom['max_sample_outside_m']<1e-5 and geom['max_radius_gap_m']<.003
 for r in [best,safe]:
  r['baseline_m']=math.hypot(r['x'],r['y']);r['bearing_deg']=math.degrees(math.atan2(r['y'],r['x']));r['move_time_s']=r['baseline_m']/5;r['rms_radius_m']=math.sqrt(r['J']/math.pi)
 out={'status':'numerically_verified_grid_minimum_not_global_certificate','main':best,'safe':safe,'safe_relative_area_increase':safe['J']/best['J']-1,'candidates':{},'prior_sensitivity':[],'checks':checks}
 for pct in [1,5]:
  a=rows(f'results/candidates_{pct}pct.csv');short=min(a,key=lambda r:r['x']**2+r['y']**2)
  out['candidates'][str(pct)]={'count_upper_half_plane':len(a),'x_projection_m':[min(r['x']for r in a),max(r['x']for r in a)],'y_projection_m':[min(r['y']for r in a),max(r['y']for r in a)],'shortest_grid_point':short,'grid_step_m':5,'warning':'Projections are not an admissible rectangle. Reflect the verified discrete candidates for y<0.'}
 fixed=rows('results/sensitivity_fixed.csv')
 for idx,prior in enumerate([-1,1]):
  r={k:float(v)for k,v in json.loads((ROOT/f'results/prior_{prior}_best.json').read_text()).items()};r['prior']=prior;r['benchmark_point_loss']=fixed[idx]['J'];r['benchmark_point_regret']=fixed[idx]['J']/r['J']-1;out['prior_sensitivity'].append(r)
 (ROOT/'results/summary.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
 (ROOT/'verification/checks.json').write_text(json.dumps(checks,indent=2))
 print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
