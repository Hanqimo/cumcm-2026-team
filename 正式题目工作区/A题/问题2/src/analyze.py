"""Full-output convergence, independent analytic checks and result preparation."""
from pathlib import Path
import csv, hashlib, json, math, shutil
import numpy as np
from scipy.optimize import brentq
from scipy.special import j0,j1
ROOT=Path(__file__).resolve().parents[1]
FINAL='R006_N12800_s1024'
def data(name):return np.loadtxt(ROOT/'runs'/name/'solution_samples.csv',delimiter=',',skiprows=1)
def stats(name):return json.loads((ROOT/'runs'/name/'solution_stats.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    x=data(FINAL);assert x.shape==(10801,43) and np.array_equal(x[:,0],np.arange(10801))
    assert np.isfinite(x).all()
    checks={'model':'Q2-M01-v01','final_run':FINAL,'threshold_each_refinement':4e-6,'numeric_checks_pass':False,'physical_assumptions_validated':False,'comparisons':{},'analytic_checks':{},'independent_BDF':{}}
    rounding=[]
    for typ,name in [('space','R010_N6400_s1024'),('time','R012_N12800_s512'),('tolerance','R013_N12800_s1024_tol5e13')]:
        assert stats(name)['completed'];y=data(name);assert y.shape==x.shape;result={}
        if typ=='tolerance':
            assert stats(name)['rejected']==0 and stats(name)['steps']==stats(FINAL)['steps']
            base_diag=np.loadtxt(ROOT/'runs'/FINAL/'solution_diagnostics.csv',delimiter=',',skiprows=1)
            tol_diag=np.loadtxt(ROOT/'runs'/name/'solution_diagnostics.csv',delimiter=',',skiprows=1)
            assert np.array_equal(base_diag[:,3],tol_diag[:,3])
        for label,cols in [('T',slice(1,22)),('C',slice(22,43))]:
            d=np.abs(x[1:,cols]-y[1:,cols]);i,j=np.unravel_index(d.argmax(),d.shape)
            unequal=np.argwhere(np.round(x[1:,cols],4)!=np.round(y[1:,cols],4))
            for ti,ri in unequal:rounding.append([typ,label,int(ti+1),float(ri*.1),float(x[ti+1,cols][ri]),float(y[ti+1,cols][ri])])
            result[label]={'max_difference':float(d[i,j]),'time_s':int(i+1),'r_cm':float(j*.1),'rounding_disagreements':len(unequal)}
            assert d.max()<(1e-7 if typ=='tolerance' else 4e-6),(typ,label,d.max())
        checks['comparisons'][typ]={'reference':name,**result}
    with (ROOT/'verification/rounding_disagreements.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['comparison','field','time_s','r_cm','final_value','comparison_value']);w.writerows(rounding)
    checks['rounding_unique_positions']={z:len({(row[2],row[3]) for row in rounding if row[1]==z}) for z in ['T','C']}
    z=data('R011_N12800_s1024_tol13')
    checks['strict_tolerance_with_changed_time_grid']={'run':'R011_N12800_s1024_tol13','rejected':stats('R011_N12800_s1024_tol13')['rejected'],'max_T':float(np.max(abs(x[:,1:22]-z[:,1:22]))),'max_C':float(np.max(abs(x[:,22:]-z[:,22:]))),'status':'not a pure tolerance comparison; original 1e-7 T threshold exceeded; resolved by matched-grid 5e-13 test'}
    for mode,tag in [('bessel','V02'),('mms','V03')]:
        series=[]
        for n in [160,320,640]:
            name=f'{tag}_{mode}_N{n}';y=data(name);t=y[:,0,None];r=np.linspace(0,.02,21)[None,:]
            if mode=='bessel':
                et=brentq(lambda z:z*j1(z)-(25*.02/.4)*j0(z),1e-8,2.4048255577)
                ec=brentq(lambda z:z*j1(z)-(8e-7*.02/5e-9)*j0(z),1e-8,2.4048255577)
                T=28+.2*j0(et*r/.02)*np.exp(-(.4/3e6)*et*et*t/.02**2)
                C=1+.2*j0(ec*r/.02)*np.exp(-5e-9*ec*ec*t/.02**2)
            else:
                T=28+.4*np.exp(-t/1000)*(1+(r/.02)**2);C=1+.1*np.exp(-t/700)*(1+(r/.02)**2)
            errors=[float(np.max(abs(y[:,1:22]-T))),float(np.max(abs(y[:,22:43]-C)))]
            series.append({'N':n,'sample_error_T':errors[0],'sample_error_C':errors[1],'full_grid_errors_from_solver':[stats(name)['max_exact_error_T'],stats(name)['max_exact_error_C']]})
        for i in [1,2]:
            for f in ['T','C']:series[i]['observed_order_'+f]=math.log2(series[i-1]['sample_error_'+f]/series[i]['sample_error_'+f])
        assert all(series[-1]['sample_error_'+f]<1e-6 for f in ['T','C'])
        checks['analytic_checks'][mode]=series
    eq=stats('V01_equilibrium');assert eq['max_exact_error_T']<1e-10 and eq['max_exact_error_C']<1e-10
    checks['analytic_checks']['equilibrium']={'T':eq['max_exact_error_T'],'C':eq['max_exact_error_C']}
    for n in [400,800,1600]:
        y=data(f'V04_BDF_N{n}');delta=np.abs(y[:,1:]-x[y[:,0].astype(int),1:]);checks['independent_BDF'][str(n)]={'max_T':float(delta[:,:21].max()),'max_C':float(delta[:,21:].max()),'paper_times_T':float(delta[y[:,0]>=1800,:21].max()),'paper_times_C':float(delta[y[:,0]>=1800,21:].max())}
    a=data('V04_BDF_N800');b=data('V04_BDF_N1600');ex=(4*b[:,1:]-a[:,1:])/3;delta=abs(ex-x[b[:,0].astype(int),1:]);checks['independent_BDF']['richardson_extrapolation']={'formula':'(4*BDF1600-BDF800)/3; empirical second-order spatial cancellation, not a rigorous error bound','max_T':float(delta[:,:21].max()),'max_C':float(delta[:,21:].max())}
    assert delta.max()<4e-6
    # Differentiate the analytic manufactured flux numerically to audit the source formula.
    r=.0085;t=137.;R=.02;a=.4*math.exp(-t/1000);b=.1*math.exp(-t/700)
    def local(r):
        C=1+b*(1+(r/R)**2);T=28+a*(1+(r/R)**2);B=(650+128*C)*(1450+2736*C/(1+C));k=.21+.38*C/(1+C);D=.0024*math.exp(-.45/C-3850/(T+273.15));return T,C,B,k,D
    T,C,B,k,D=local(r);xx=(r/R)**2
    expectedT=-B*a*(1+xx)/1000-4*a/R**2*(k+b*xx*.38/(1+C)**2)
    expectedC=-b*(1+xx)/700-4*b/R**2*(D+xx*(.45*D/C**2*b+3850*D/(T+273.15)**2*a))
    def qT(z):return z*local(z)[3]*2*a*z/R**2
    def qC(z):return z*local(z)[4]*2*b*z/R**2
    dx=1e-6
    derivative=lambda f:(f(r-2*dx)-8*f(r-dx)+8*f(r+dx)-f(r+2*dx))/(12*dx)
    actualT=-B*a*(1+xx)/1000-derivative(qT)/r;actualC=-b*(1+xx)/700-derivative(qC)/r
    checks['manufactured_source_flux_difference']={'r_m':r,'time_s':t,'step_m':dx,'source_T':expectedT,'source_C':expectedC,'absolute_difference_T':abs(actualT-expectedT),'absolute_difference_C':abs(actualC-expectedC)}
    assert abs(actualT-expectedT)<1e-6 and abs(actualC-expectedC)<1e-12
    s=stats(FINAL);assert s['completed'] and s['end_time']==10800 and s['linear_backward_error']<1e-12
    d=np.loadtxt(ROOT/'runs'/FINAL/'solution_diagnostics.csv',delimiter=',',skiprows=1)
    checks['balance']={'heat_J':s['cumulative_heat_balance_per_2piL']*2*math.pi*.25,'normalized_water_balance':s['cumulative_water_balance_per_rhod_2piL'],'mean_moisture_identity_error':float(d[-1,2]-2.55+2/.02**2*s['cumulative_water_per_rhod_2piL']),'heat_relative':abs(s['cumulative_heat_balance_per_2piL']/s['cumulative_heat_per_2piL']),'water_relative':abs(s['cumulative_water_balance_per_rhod_2piL']/s['cumulative_water_per_rhod_2piL'])}
    assert checks['balance']['heat_relative']<1e-9 and checks['balance']['water_relative']<1e-9
    checks['numeric_checks_pass']=True
    (ROOT/'verification/checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    rowsT=[];rowsC=[]
    for t in range(1800,10801,1800):rowsT.append([t/3600,*x[t,[1,6,11,16,21]]]);rowsC.append([t/3600,*x[t,[22,27,32,37,42]]])
    for filename,rows in [('表3_温度.csv',rowsT),('表4_含水率.csv',rowsC)]:
        with (ROOT/'results'/filename).open('w',encoding='utf-8-sig') as f:
            w=csv.writer(f);w.writerow(['时间_h','0_cm','0.5_cm','1_cm','1.5_cm','2_cm']);w.writerows(rows)
    shutil.copy2(ROOT/'runs'/FINAL/'solution_samples.csv',ROOT/'results/full_precision.csv')
    shutil.copy2(ROOT/'runs'/FINAL/'solution_final.csv',ROOT/'results/final_internal_grid.csv')
    shutil.copy2(ROOT/'runs'/FINAL/'solution_diagnostics.csv',ROOT/'results/diagnostics.csv')
    payload={}
    for name,cols in [('温度',slice(1,22)),('水分浓度',slice(22,43))]:payload[name]=[['时间\\到药材中心的距离',*np.round(np.arange(21)*.1,1).tolist()]]+[[int(t),*vals.tolist()] for t,vals in zip(x[1:,0],x[1:,cols])]
    (ROOT/'results/workbook_payload.json').write_text(json.dumps(payload,ensure_ascii=False))
    summary={'model':'Q2-M01-v01','final_run':FINAL,'stats':s,'table3':rowsT,'table4':rowsC,'mean_T_3h':float(d[-1,1]),'mean_C_3h':float(d[-1,2]),'fraction_of_initial_water_removed':float(1-d[-1,2]/2.55),'sources':{f:str(Path('../runs')/FINAL/f) for f in ['solution_samples.csv','solution_final.csv','solution_diagnostics.csv']},'source_sha256':{f:sha(ROOT/'runs'/FINAL/f) for f in ['solution_samples.csv','solution_final.csv','solution_diagnostics.csv']}}
    (ROOT/'results/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({'checks':checks,'summary':summary},ensure_ascii=False))
if __name__=='__main__':main()
