"""Analytical special cases, deliberately under-iterated step, and full-output comparisons.
The analytical references use convergent Bessel power series and explicit closed-form states.
No PDE numerical results are fed back as analytical reference values.
"""
from pathlib import Path
import json, math
import numpy as np
def bj(order,x):
 x=np.asarray(x,dtype=float);term=np.ones_like(x) if order==0 else x/2;total=term.copy()
 for k in range(1,40):
  term=term*(-x*x/4)/(k*(k+order));total+=term
 return total
def j0(x):return bj(0,x)
def j1(x):return bj(1,x)
def characteristic_root(fn,a,b):
 # Deterministic bisection of the analytic characteristic equation.
 for _ in range(80):
  c=(a+b)/2
  if fn(c)>0:b=c
  else:a=c
 return (a+b)/2
ROOT=Path(__file__).resolve().parents[1]
def load(name,area='runs'):
 return np.loadtxt(ROOT/area/name/'solution_samples.csv',delimiter=',',skiprows=1)
def compare(a,b,field):
 x,y=load(a),load(b);assert x.shape==y.shape==(1801,43)
 assert np.array_equal(x[:,0],np.arange(1801)) and np.array_equal(x[:,0],y[:,0])
 k=1 if field=='T' else 22;u,v=x[1:,k:k+21],y[1:,k:k+21];d=abs(u-v);i,j=np.unravel_index(d.argmax(),d.shape)
 z=np.argwhere(np.round(u,4)!=np.round(v,4))
 return dict(coarse=a,fine=b,field=field,max_difference=float(d[i,j]),time_s=int(i+1),radius_cm=float(j/10),coarse_value=float(u[i,j]),fine_value=float(v[i,j]),four_decimal_disagreements=len(z),first_10_disagreements=[dict(time_s=int(p+1),radius_cm=float(q/10),coarse=float(u[p,q]),fine=float(v[p,q])) for p,q in z[:10]])
def analytical():
 records=[]
 for mode in ['bessel','mms']:
  for n in [80,160,320]:
   name=f'{mode}_N{n}';a=load(name,'verification');r=np.linspace(0,.02,21)[None,:];t=a[:,0,None]
   if mode=='bessel':
    rt=characteristic_root(lambda x:x*j1(x)-(25*.02/.36)*j0(x),1e-12,2.40482555769577)
    rc=characteristic_root(lambda x:x*j1(x)-(8e-7*.02/5e-9)*j0(x),1e-12,2.40482555769577)
    T=28+5*j0(rt*r/.02)*np.exp(-(.36/(820*2600))*rt*rt*t/.02**2)
    C=1+.2*j0(rc*r/.02)*np.exp(-5e-9*rc*rc*t/.02**2)
   else:T=28+np.zeros_like(t*r);C=1+.1*np.exp(-t/100)*(1+(r/.02)**2)
   s=json.loads((ROOT/'verification'/name/'solution_stats.json').read_text())
   records.append(dict(mode=mode,N=n,dt=s['base_dt'],sample_error_T=float(abs(a[:,1:22]-T).max()),sample_error_C=float(abs(a[:,22:43]-C).max()),all_nodes_integer_times_error_T=s['exact_max_error_T'],all_nodes_integer_times_error_C=s['exact_max_error_C']))
 for mode in ['bessel','mms']:
  rows=[r for r in records if r['mode']==mode]
  for i in [1,2]:
   rows[i]['observed_space_order_C']=math.log2(rows[i-1]['all_nodes_integer_times_error_C']/rows[i]['all_nodes_integer_times_error_C'])
   if mode=='bessel':rows[i]['observed_space_order_T']=math.log2(rows[i-1]['all_nodes_integer_times_error_T']/rows[i]['all_nodes_integer_times_error_T'])
 eq=load('equilibrium','verification');return dict(analytical_cases=records,equilibrium_max_error_T=float(abs(eq[:,1:22]-28).max()),equilibrium_max_error_C=float(abs(eq[:,22:43]-2.55).max()))
def underiteration():
 # Same model constants, first step. Deliberately use D(old) only once.
 n=200;dt=.25;R=.02;hm=8e-7;dr=R/n;r=np.arange(n+1)*dr
 faces=np.r_[0,(np.arange(n)+.5)*dr,R];w=np.diff(faces**2)/2;mu=w/dt;old=np.full(n+1,2.55)
 env=np.loadtxt(ROOT/'inputs/environment.csv',delimiter=',',skiprows=1);Ce=float(np.interp(dt,env[:,0],env[:,2]))
 D=lambda c:7e-9*np.exp(-.89/c)
 conduct=lambda c:(np.arange(n)+.5)*(D(c[:-1])+D(c[1:]))/2
 g=conduct(old);diag=mu+np.r_[0,g]+np.r_[g,R*hm];ab=np.zeros((3,n+1));ab[0,1:]=-g;ab[1]=diag;ab[2,:-1]=-g
 rhs=mu*old;rhs[-1]+=R*hm*Ce;candidate=np.linalg.solve(np.diag(diag)+np.diag(-g,1)+np.diag(-g,-1),rhs)
 gnew=conduct(candidate);F=mu*(candidate-old);flow=gnew*np.diff(candidate);F[:-1]-=flow;F[1:]+=flow;F[-1]-=R*hm*(Ce-candidate[-1]);diagnew=mu+np.r_[0,gnew]+np.r_[gnew,R*hm]
 residual=float(np.max(abs(F)/diagnew));eps_paper=1e-10+1e-9*np.max(abs(candidate));balance=float(np.sum(w.astype(np.longdouble)*(candidate-old))-np.longdouble(dt)*R*hm*(Ce-candidate[-1]))
 return dict(N=n,dt=dt,time_s=dt,Ce=Ce,surface_candidate=float(candidate[-1]),single_frozen_solve_water_balance=balance,scaled_original_nonlinear_residual=residual,paper_tolerance=float(eps_paper),ratio_to_paper_tolerance=float(residual/eps_paper),ratio_to_actual_tolerance=float(residual/(1e-12*(1+np.max(abs(candidate))))),expected_accept=False,reason='Recomputed nonlinear residual and update fail even though the global frozen-system balance cancels.')
def main():
 checks=analytical();checks['underiteration']=underiteration()
 pairs=[('review_time','R002_N200_dt05','R001_N200_dt025','TC'),('review_space','R001_N200_dt025','R003_N400_dt025','TC'),
 ('T_time_coarse','R_N1600_s32768','R_N1600_s65536','T'),('T_time_final','R_N1600_s65536','R_N1600_s131072','T'),('T_space_coarse','R_N400_s65536','R_N800_s65536','T'),('T_space_middle','R_N800_s65536','R_N1600_s65536','T'),('T_space_final','R_N800_s131072','R_N1600_s131072','T'),
 ('C_time_coarse','R_N12800_s2048','R_N12800_s4096','C'),('C_time_final','R_N12800_s4096','R_N12800_s8192','C'),('C_space_coarse','R_N3200_s8192','R_N6400_s8192','C'),('C_space_final','R_N6400_s8192','R_N12800_s8192','C')]
 checks['comparisons']={f'{label}_{f}':compare(a,b,f) for label,a,b,fields in pairs for f in fields if (ROOT/'runs'/b/'solution_stats.json').exists() and (ROOT/'runs'/a/'solution_stats.json').exists()}
 for f in ['T','C']:
  for dimension in ['time','space']:
   a=checks['comparisons'].get(f'{f}_{dimension}_coarse_{f}');b=checks['comparisons'].get(f'{f}_{dimension}_final_{f}')
   if a and b:
    middle=checks['comparisons'].get(f'{f}_{dimension}_middle_{f}',b)
    b['observed_order']=math.log2(a['max_difference']/middle['max_difference']);b['order_note']='T space order measured at fixed s65536; final space check at fixed s131072' if f=='T' and dimension=='space' else 'same other discretization parameter'
    b['passes_4e_6']=b['max_difference']<=4e-6
 tight='R_N12800_s8192_tol13'
 if (ROOT/'runs'/tight/'solution_stats.json').exists():checks['tightening']=compare('R_N12800_s8192',tight,'C');checks['tightening']['passes_1e_7']=checks['tightening']['max_difference']<=1e-7
 (ROOT/'verification/checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(checks,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
