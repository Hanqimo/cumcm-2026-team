"""Finite candidate search, baselines, outer-bound refinement and stress tests."""
from pathlib import Path
import sys, json, csv, argparse, hashlib, platform, subprocess, time
from datetime import datetime,timezone
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from second_point import (ROOT,unit,to_global,to_local,candidate_margins,in_candidate,
    first_region,posterior,worst_radius_upper,bearing,angle_difference,enclosing_circle)

MODEL=Path(__file__).resolve().parents[1]


def csv_write(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',default='R001');ap.add_argument('--quick',action='store_true');args=ap.parse_args()
    out=MODEL/'runs'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter();seed=20260910;rng=np.random.default_rng(seed)
    epsilon=1.;sides=360;h=20.;budgets=[250.,500.,750.,1000.]
    sensor=np.array([0.,0.]);theta=0.;poly=first_region(sides=sides)
    checks=[]
    def check(name,ok,details=None):
        checks.append(dict(name=name,passed=bool(ok),details=details))
        if not ok:raise AssertionError((name,details))

    # Independent direct-distance check of analytical reception region.
    local_candidates=[]
    radii=[100,200,250,300,400,500,600,700,750,800,900,1000]
    for step in radii:
        for alpha in np.arange(5,86,5):
            local=step*unit(alpha)
            if in_candidate(local,lateral_min=h):local_candidates.append(local)
    radial=np.r_[5.0001,np.linspace(10,1500,101),999.999,1000,1000.001]
    phi=np.linspace(-epsilon,epsilon,51)
    targets=np.concatenate([r*np.array([unit(a) for a in phi]) for r in radial])
    receiver_min=np.maximum(1000,np.linalg.norm(targets,axis=1))
    worst_reception_margin=np.inf
    for local in local_candidates:
        worst_reception_margin=min(worst_reception_margin,float(np.min(receiver_min-np.linalg.norm(targets-local,axis=1))))
    check('direct_distance_reception_grid',worst_reception_margin>=-1e-7,worst_reception_margin)
    # Counterexample to perpendicular-only move; first reception really possible.
    blind_target=np.array([1000.,0.]);blind_q=np.array([0.,500.])
    check('perpendicular_move_can_lose_signal',np.linalg.norm(blind_target-blind_q)>1000)
    # Exact disk-membership expression versus local inequality (different form).
    for _ in range(200):
        a,b=rng.uniform([-200,-1200],[1200,1200]);v=np.array([a,b]);e=np.deg2rad(epsilon)
        analytic=(a*a+b*b<=1000**2+1e-8 and a*a+b*b<=2000*(a*np.cos(e)-abs(b)*np.sin(e))+1e-8)
        geometric=(np.linalg.norm(v)<=1000+1e-9 and all(np.linalg.norm(v-1000*unit(t))<=1000+1e-9 for t in [-epsilon,epsilon]))
        check('candidate_disk_equivalence',analytic==geometric)

    coarse=[]
    for index,local in enumerate(local_candidates):
        score=worst_radius_upper(poly,local,bin_width_deg=1. if args.quick else .5)
        coarse.append(dict(a_m=float(local[0]),b_m=float(local[1]),travel_m=float(np.linalg.norm(local)),
          alpha_deg=float(np.rad2deg(np.arctan2(local[1],local[0]))),radius_upper_m=score['radius_upper_m']))
        if index%30==0:print(f'coarse {index+1}/{len(local_candidates)}',flush=True)
    csv_write(out/'coarse_candidates.csv',coarse)
    selected=[];refined_all=[]
    for budget in budgets:
        eligible=[r for r in coarse if r['travel_m']<=budget+1e-7]
        top=sorted(eligible,key=lambda r:r['radius_upper_m'])[:2]
        pool={}
        for row in top:
            for length in np.arange(max(25,row['travel_m']-50),min(budget,row['travel_m']+50)+1,25):
                for alpha in np.arange(max(2,row['alpha_deg']-5),min(88,row['alpha_deg']+5)+.01,2):
                    local=length*unit(alpha)
                    if in_candidate(local,budget=budget,lateral_min=h):pool[(round(length,6),round(alpha,6))]=local
            pool[(round(row['travel_m'],6),round(row['alpha_deg'],6))]=np.array([row['a_m'],row['b_m']])
        best=None
        for local in pool.values():
            result=worst_radius_upper(poly,local,bin_width_deg=.5 if args.quick else .2)
            row={'budget_m':budget,'a_m':float(local[0]),'b_m':float(local[1]),'travel_m':float(np.linalg.norm(local)),'radius_upper_m':result['radius_upper_m']}
            refined_all.append(row)
            if best is None or row['radius_upper_m']<best['radius_upper_m']:best=row
        # Reading-bin refinement can change the ranking. Re-rank a shortlist at
        # final resolution and explicitly retain the safe 45-degree baseline.
        shortlist=sorted([r for r in refined_all if r['budget_m']==budget],key=lambda r:r['radius_upper_m'])[:6]
        diag=budget*unit(45.)
        shortlist.append(dict(budget_m=budget,a_m=float(diag[0]),b_m=float(diag[1]),travel_m=budget))
        final=None
        for trial in shortlist:
            loc=np.array([trial['a_m'],trial['b_m']])
            candidate=worst_radius_upper(poly,loc,bin_width_deg=.2 if args.quick else .05)
            if final is None or candidate['radius_upper_m']<final['radius_upper_m']:
                best=trial.copy();final=candidate
        local=np.array([best['a_m'],best['b_m']])
        best.update(radius_upper_m=final['radius_upper_m'],bin_width_deg=final['bin_width_deg'],
          movement_and_measure_s=best['travel_m']/5+5,alpha_deg=float(np.rad2deg(np.arctan2(local[1],local[0]))),
          candidate_margin_min_m=min(candidate_margins(local,budget=budget,lateral_min=h).values()))
        selected.append(best)
        (out/f'worst_enclosure_B{int(budget)}.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
        print('selected',best,flush=True)
    csv_write(out/'refined_candidates.csv',refined_all)
    csv_write(out/'selected_points.csv',selected)

    # Same travel budgets; both safe and deliberately unsafe elementary baselines.
    baseline_rows=[]
    for budget in budgets:
        for name,alpha in [('forward',0.),('diagonal_45',45.),('perpendicular',90.)]:
            local=budget*unit(alpha)
            result=worst_radius_upper(poly,local,bin_width_deg=.2 if args.quick else .05)
            baseline_rows.append(dict(budget_m=budget,method=name,a_m=float(local[0]),b_m=float(local[1]),
              conditional_radius_upper_m=result['radius_upper_m'],
              guaranteed_reception=bool(np.linalg.norm(local)<=1000+1e-8 and min(np.linalg.norm(local-1000*unit(a)) for a in [-epsilon,epsilon])<=1000+1e-8 and max(np.linalg.norm(local-1000*unit(a)) for a in [-epsilon,epsilon])<=1000+1e-8)))
    csv_write(out/'baselines.csv',baseline_rows)

    # Conditional scenarios, not an assumed distribution of official targets.
    # Fix the first reading to zero, vary the true angle, range, radius and second error.
    stress=[];max_coverage_violation=0.;max_bound_violation=0.
    for row in selected:
        q=np.array([row['a_m'],row['b_m']]);max_r=0.;mean_rs=[];nosignal=0;near=0;clearable=0
        for distance in [5.01,20,100,250,500,750,999,1000,1001,1250,1499.99]:
            for phi0 in [-1,-.5,0,.5,1]:
                x=distance*unit(phi0)
                R=max(1000.,distance)
                d2=np.linalg.norm(x-q)
                if d2>R+1e-7:nosignal+=1;continue
                if d2<=5:near+=1;continue
                for error in [-1,-.5,0,.5,1]:
                    reading=(bearing(x,q)+error)%360
                    post=posterior(poly,q,reading)
                    check('stress_posterior_nonempty',len(post)>0)
                    c,r,_=enclosing_circle(post)
                    max_coverage_violation=max(max_coverage_violation,float(np.linalg.norm(x-c)-r))
                    max_bound_violation=max(max_bound_violation,r-row['radius_upper_m'])
                    max_r=max(max_r,r);mean_rs.append(r);clearable+=int(r<=20)
                    stress.append(dict(budget_m=row['budget_m'],range_m=distance,true_angle_deg=phi0,second_error_deg=error,
                      radius_m=r,target_distance_to_center_m=float(np.linalg.norm(x-c)),reception_radius_m=R))
        row.update(sample_max_radius_m=max_r,sample_mean_radius_m=float(np.mean(mean_rs)),sample_no_signal_count=nosignal,
          sample_near_count=near,sample_clearable_count=clearable,sample_direction_count=len(mean_rs))
    check('stress_true_target_covered',max_coverage_violation<1e-6,max_coverage_violation)
    check('continuous_bin_bound_dominates_samples',max_bound_violation<1e-6,max_bound_violation)
    csv_write(out/'stress_cases.csv',stress);csv_write(out/'selected_points.csv',selected)

    # Resolution and rounding sensitivity at the B=500 recommendation.
    q=np.array([selected[1]['a_m'],selected[1]['b_m']]);sensitivity=[]
    for nsides,eps,delta in [(180,1.,.2),(360,1.,.2),(720,1.,.2),(360,1.,.5),(360,1.,.1),(360,1.,.05),(360,1.005,.05),
                            (360,.5,.05),(360,1.5,.05)]:
        p=first_region(epsilon_deg=eps,sides=nsides)
        score=worst_radius_upper(p,q,epsilon_deg=eps,bin_width_deg=delta)
        sensitivity.append(dict(disk_sides=nsides,epsilon_deg=eps,reading_bin_deg=delta,radius_upper_m=score['radius_upper_m'],
          candidate_still_valid=in_candidate(q,epsilon_deg=eps,budget=500,lateral_min=h)))
    csv_write(out/'sensitivity.csv',sensitivity)

    # Changed absolute position/reading affects the arena prior. Re-evaluate,
    # rather than assuming one normalized optimum works everywhere.
    contexts=[]
    for s,theta2 in [([0.,0.],90.),([1600.,0.],0.),([1600.,0.],180.)]:
        p=first_region(s,theta2,sides=360)
        u=to_global(q,s,theta2)
        score=worst_radius_upper(p,u,bin_width_deg=.1)
        contexts.append(dict(sensor=s,reading_deg=theta2,point=u.tolist(),radius_upper_m=score['radius_upper_m']))
    (out/'context_checks.json').write_text(json.dumps(contexts,indent=2),encoding='utf-8')
    check('rotated_center_context',abs(contexts[0]['radius_upper_m']-next(r['radius_upper_m'] for r in sensitivity if r['disk_sides']==360 and r['epsilon_deg']==1 and r['reading_bin_deg']==.1))<1e-5)

    # Figures consume saved arrays, not manually entered result numbers.
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),constrained_layout=True)
    ax=axes[0];xx,yy=np.meshgrid(np.linspace(-100,1050,300),np.linspace(-1050,1050,400));e=np.deg2rad(epsilon)
    mask=(xx*xx+yy*yy<=1e6)&(xx*xx+yy*yy<=2000*(xx*np.cos(e)-np.abs(yy)*np.sin(e)))&(np.abs(yy)*np.cos(e)-xx*np.sin(e)>=h)
    ax.contourf(xx,yy,mask.astype(int),levels=[.5,1.5],colors=['#d6eaf8'])
    ax.plot([0,1500],[0,0],ls='--',color='gray',label='First bearing')
    for row in selected:ax.scatter(row['a_m'],row['b_m'],s=45);ax.annotate(f"B={int(row['budget_m'])}",(row['a_m']+15,row['b_m']+15),fontsize=8)
    ax.set(xlabel='Along first bearing a (m)',ylabel='Lateral displacement b (m)',title='Guaranteed reception candidate region',xlim=(-100,1100));ax.set_aspect('equal');ax.grid(alpha=.2)
    ax=axes[1];ax.plot([r['budget_m'] for r in selected],[r['radius_upper_m'] for r in selected],'-o',label='Finite minimax search')
    for name in ['diagonal_45','forward']:
        rows=[r for r in baseline_rows if r['method']==name]
        ax.plot([r['budget_m'] for r in rows],[r['conditional_radius_upper_m'] for r in rows],'-o',label=name)
    ax.axhline(20,color='#117864',ls='--',label='20 m clearance radius');ax.set(xlabel='Travel budget (m)',ylabel='Worst posterior radius upper bound (m)',title='One additional bearing: quality vs travel');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.savefig(out/'q2_candidate_and_tradeoff.png',dpi=220);fig.savefig(out/'q2_candidate_and_tradeoff.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4),constrained_layout=True)
    for row in selected:
        rows=[r for r in stress if r['budget_m']==row['budget_m']]
        ranges=sorted(set(r['range_m'] for r in rows));rs=[max(r['radius_m'] for r in rows if r['range_m']==d) for d in ranges]
        ax.plot(ranges,rs,'-o',ms=3,label=f"B={int(row['budget_m'])}")
    ax.axhline(20,color='gray',ls='--');ax.set(xlabel='True range from first sensor (m)',ylabel='Maximum over scenario errors (m)',title='Synthetic conditional stress cases');ax.legend();ax.grid(alpha=.2)
    fig.savefig(out/'q2_range_stress.png',dpi=220);fig.savefig(out/'q2_range_stress.svg');plt.close(fig)

    report=dict(checks=checks,count=len(checks),passed=all(x['passed'] for x in checks),
      worst_reception_margin_m=worst_reception_margin,target_coverage_violation_m=max_coverage_violation,
      upper_bound_violation_m=max_bound_violation,elapsed_s=time.perf_counter()-started,
      caveats=['Synthetic conditional cases, not official simulator tests','Finite spatial search, no continuous global-optimum claim',
      'Bounds use outer polygons and expanded bearing bins; floating-point residuals are not interval-certified'])
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[Path(__file__),MODEL/'src/second_point.py',ROOT/'contest/q1/models/m01-bounded-bearing/src/bearing_geometry.py']
    snapshot=out/'source_snapshot';snapshot.mkdir()
    for p in files:(snapshot/p.name).write_bytes(p.read_bytes())
    manifest=dict(model='Q2-M01-v01',algorithm='A01-finite-candidates-outer-reading-bins',data='D01-synthetic-first-bearing',run=args.run_id,
      seed=seed,utc=datetime.now(timezone.utc).isoformat(),command='python '+str(Path(__file__).relative_to(ROOT))+' --run-id '+args.run_id+(' --quick' if args.quick else ''),
      base_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),uncommitted_source=True,
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
      versions={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__},
      configuration={'epsilon_deg':epsilon,'disk_sides':sides,'lateral_min_m':h,'budgets_m':budgets,'quick':args.quick},validation='passed')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(count=report['count'],passed=report['passed'],elapsed_s=report['elapsed_s'],selected=selected),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
