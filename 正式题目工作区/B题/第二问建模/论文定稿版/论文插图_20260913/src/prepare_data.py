"""Fixed-point figure data only; preserves the frozen solver and candidate table."""
from pathlib import Path
import subprocess, json, csv, math, sys, hashlib
ROOT=Path(__file__).resolve().parents[1]
try: import numpy as np
except ImportError:
 sys.path.insert(0,'/private/tmp/bq2-plot-deps'); import numpy as np
raw=(ROOT/'inputs/trial_solver.cpp').read_text()
assert raw.count('int main(int argc,char**argv){')==1
extension=r'''
int main(int argc,char**argv){
 SCENARIO_A=0;SCENARIO_BETA=0;TARGET_CENTER={0,0};ZC=normalizer();
 P q={813.824371479152,521.018510869701};string mode=argv[1];
 cout<<setprecision(16);
 if(mode=="eval"){trial_header();trial_evaluate(q,6,128);}
 else if(mode=="cuts"){TrialEvaluator e{q,settings(5),128};auto t=e.breaks();cout<<"[";for(size_t i=0;i<t.size();i++)cout<<(i?",":"")<<t[i];cout<<"]";}
 else if(mode=="profile"){
  cout<<"theta_rad,theta_deg,pdf_rad,pdf_deg,rho_lower,rho_upper,center_x,center_y,dmax\n";
  double t;while(cin>>t){auto v=feedback(q,1,t);auto sh=boundary(v);double m=mass(v,sh,q,1,20,28)/(2*A*ZC);
   cout<<t<<","<<t*180/PI<<","<<m<<","<<m*PI/180;
   if(sh.points.empty())cout<<",nan,nan,nan,nan,nan\n";
   else{auto c=continuous_mec(sh);cout<<","<<c.lo<<","<<c.hi<<","<<c.c.x<<","<<c.c.y<<","<<norm(farthest(sh,q)-q)<<"\n";}
  }
 }
 else if(mode=="geometry"){
  double t=stod(argv[2])*PI/180;auto v=feedback(q,1,t);auto s=boundary(v);auto c=continuous_mec(s);
  cout<<"{\"theta_deg\":"<<stod(argv[2])<<",\"radius_lower\":"<<c.lo<<",\"radius_upper\":"<<c.hi<<",\"dmax\":"<<norm(farthest(s,q)-q)<<",\"center\":["<<c.c.x<<","<<c.c.y<<"],\"points\":[";
  for(size_t i=0;i<s.points.size();i++){if(i)cout<<",";cout<<"["<<s.points[i].x<<","<<s.points[i].y<<"]";}
  cout<<"],\"arcs\":[";for(size_t i=0;i<s.arcs.size();i++){auto a=s.arcs[i];if(i)cout<<",";cout<<"["<<a.o.x<<","<<a.o.y<<","<<a.r<<","<<a.l<<","<<a.h<<"]";}cout<<"]}";
 }
 else if(mode=="normalizer")cout<<ZC;
 return 0;
}
'''
p=ROOT/'src/figure_kernel.cpp';p.write_text(raw.replace('int main(int argc,char**argv){','int frozen_trial_main(int argc,char**argv){')+extension)
binary=ROOT/'src/figure_kernel';subprocess.run(['clang++','-O3','-std=c++17',str(p),'-o',str(binary)],check=True)
def run(mode,*args,inp=None):
 return subprocess.run([str(binary),mode,*map(str,args)],input=inp,text=True,capture_output=True,check=True).stdout
cuts=json.loads(run('cuts'));(ROOT/'data/angular_cuts.json').write_text(json.dumps(cuts,indent=2))
# Include breakpoints plus immediate one-sided values; maximum spacing 0.02 degrees.
theta=[]
for l,h in zip(cuts[:-1],cuts[1:]):
 n=max(3,math.ceil((h-l)*180/math.pi/.02))
 theta.extend(np.linspace(l,h,n+1))
 if h-l>1e-10:theta.extend([l+1e-10,h-1e-10])
theta=sorted(set(map(float,theta)))
(ROOT/'data/feedback_profile.csv').write_text(run('profile',inp='\n'.join(format(t,'.17g') for t in theta)))
(ROOT/'data/representative_evaluation.csv').write_text(run('eval'))
for deg in [270,300]:
 (ROOT/f'data/geometry_{deg}.json').write_text(run('geometry',deg))
alpha=math.pi/180
integral=(1000**2-5**2)/2+(1500*(1500**2-1000**2)/2-(1500**3-1000**3)/3)/500
C1=2*alpha*integral
kernel=float(run('normalizer'))
profile=np.genfromtxt(ROOT/'data/feedback_profile.csv',delimiter=',',names=True)
evaluation=next(csv.DictReader((ROOT/'data/representative_evaluation.csv').open()))
x=profile['theta_deg'];y=profile['pdf_deg'];r=profile['rho_upper']
# Threshold roots are included. Midpoint classification on each short interval avoids endpoint ambiguity.
complete=(r[:-1]+r[1:])/2<=20
masses=np.diff(x)*(y[:-1]+y[1:])/2
checks={'C1_analytic_m2':C1,'C1_kernel_m2':kernel,'C1_difference':kernel-C1,'density_max_per_m2':1/C1,'profile_sample_count':len(theta),'normal_probability_trapezoid':float(masses.sum()),'completion_probability_trapezoid':float(masses[complete].sum()),'completion_probability_kernel':float(evaluation['P_finish']),'J_trapezoid_m':float(np.sum(np.diff(x)*np.nan_to_num(y[:-1]*r[:-1]+y[1:]*r[1:])/2)),'J_kernel_m':float(evaluation['J']),'P_H':float(evaluation['P_H']),'P_N':float(evaluation['P_N']),'P_onsite':float(evaluation['P_onsite']),'exact_geometry':{str(d):json.loads((ROOT/f'data/geometry_{d}.json').read_text()) for d in [270,300]}}
assert abs(kernel-C1)<1e-7
assert abs(masses.sum()-1)<1e-5
assert abs(masses[complete].sum()-float(evaluation['P_finish']))<1e-5
assert checks['P_H']==checks['P_N']==checks['P_onsite']==0
assert checks['exact_geometry']['270']['radius_upper']<20<checks['exact_geometry']['300']['radius_upper']
(ROOT/'verification/numerical_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in checks.items() if k!='exact_geometry'},indent=2))
print('Geometry:',[(d,checks['exact_geometry'][str(d)]['radius_upper']) for d in [270,300]])
