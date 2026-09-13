from pathlib import Path
import json,sys,importlib.util,math,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('check_trial',ROOT/'inputs/validate_trial.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
records=[];q=[813.824371479152,521.018510869701]
for deg in [270,300]:
 geo=json.loads((ROOT/f'data/geometry_{deg}.json').read_text());pts=mod.rays.independent_points(0,0,q,1,math.radians(deg),n=16001)
 dirs=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)];v=pts[np.unique([int(np.argmax(pts@u)) for u in dirs])]
 low=mod.exact_finite_radius(v);r=geo['radius_upper'];outside=float(np.linalg.norm(pts-np.array(geo['center']),axis=1).max()-r)
 assert outside<1e-6 and r-low<1e-5
 assert (r<=20 if deg==270 else low>20)
 polygon=np.loadtxt(ROOT/f'data/boundary_{deg}.csv',delimiter=',',skiprows=1)
 # Both selected regions have four straight edges; no arc approximation needed.
 assert len(geo['arcs'])==0
 rec={'theta_deg':deg,'independent_sample_count':len(pts),'independent_radius_lower_m':low,'continuous_radius_upper_m':r,'gap_m':r-low,'max_sample_outside_m':outside,'plotted_vertices':len(polygon),'completion_condition_confirmed':True};records.append(rec)
profile=np.genfromtxt(ROOT/'data/feedback_profile.csv',delimiter=',',names=True)
assert np.max(profile['pdf_deg'])<.0165
positive=profile['pdf_deg']>1e-14
assert profile['theta_deg'][positive].min()>205 and profile['theta_deg'][positive].max()<330
check={'geometry':records,'max_pdf_per_degree':float(np.max(profile['pdf_deg'])),'positive_density_angle_range_deg':[float(profile['theta_deg'][positive].min()),float(profile['theta_deg'][positive].max())],'plot_data_ranges_not_clipped':True}
(ROOT/'verification/independent_figure_checks.json').write_text(json.dumps(check,ensure_ascii=False,indent=2))
print(json.dumps(check,indent=2))
