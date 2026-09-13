"""运行第一、二问的数值验证，并保存可核查报告。"""
from pathlib import Path
import argparse,csv,hashlib,json,math,platform,time
import numpy as np
import scipy
from q1.validation import run as validate_q1
from q1.validate_projection import run as validate_projection
from q1.bearing_geometry import Region,summarize_region
from q2.api import evaluate,initial_geometry,feedback_geometry,native
from q2.independent_geometry import independent_points,exact_finite_radius
ROOT=Path(__file__).resolve().parent


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report={'q1_geometry':validate_q1(out/'q1_geometry'),'q1_projection':validate_projection(out/'q1_projection')}
    edge=summarize_region(Region('segment',np.array([[-20.,0],[20.,0]])))
    assert edge['guaranteed_clear_possible'],'rho=20 must pass physical criterion'
    report['q1_radius_20_boundary']=edge
    convergence=[]
    references=[]
    for name in ['origin_weights.csv','typical_cases.csv']:
        references.extend(list(csv.DictReader((ROOT/'reference_results'/name).open())))
    for r in references:
        a,b=float(r['a_m']),float(r['beta_deg']);q=[float(r['x']),float(r['y'])]
        lo=evaluate(a,b,q,level=5,scan=64,frame='internal')
        hi=evaluate(a,b,q,frame='internal')
        record={'a':a,'beta_deg':b,'q_internal':q,'w':float(r['w']),
                'J_reference_difference_m':hi['J']-float(r['J']),
                'P_reference_difference':hi['P_finish']-float(r['P_finish']),
                'J_precision_difference_m':hi['J']-lo['J'],
                'P_precision_difference':hi['P_finish']-lo['P_finish'],
                'evaluation':hi}
        assert abs(record['J_reference_difference_m'])<1e-5,record
        assert abs(record['P_reference_difference'])<2e-6,record
        assert abs(record['J_precision_difference_m'])<1e-5,record
        assert abs(record['P_precision_difference'])<2e-6,record
        assert abs(hi['probability_residual'])<1e-7,record
        assert -1e-7<=hi['P_finish']<=1+1e-7,record
        assert hi['P_finish']>=max(hi['P_onsite'],hi['P_H'])-1e-7,record
        convergence.append(record)
    report['q2_reference_and_convergence']=convergence
    q=[813.824371479152,521.018510869701];north=evaluate(0,0,q);south=evaluate(0,0,[q[0],-q[1]])
    assert abs(north['J']-south['J'])<1e-5 and abs(north['P_finish']-south['P_finish'])<2e-6
    report['q2_symmetry']={'J_difference_m':north['J']-south['J'],'P_difference':north['P_finish']-south['P_finish']}
    strong=evaluate(0,0,[700,0]);geo=feedback_geometry(0,0,[700,0],'H')
    assert strong['P_H']>0 and geo['radius_upper']>0 and strong['J']>0
    report['q2_strong_signal']={'evaluation':strong,'strong_radius_m':geo['radius_upper'],'strong_J_contribution_m':strong['P_H']*geo['radius_upper']}
    no_signal=evaluate(1700,0,[-930,0],frame='internal');geo=feedback_geometry(1700,0,[-930,0],'N',frame='internal')
    assert no_signal['P_N']>0 and abs(no_signal['P_finish_N']-no_signal['P_N'])<1e-10 and geo['radius_upper']<20 and geo['dmax']>1000
    report['q2_no_signal_completion']={'evaluation':no_signal,'geometry':geo}
    assert initial_geometry(1780,0)['rho1']<20
    try:initial_geometry(4000,0)
    except ValueError:pass
    else:raise AssertionError('impossible first observation accepted')
    try:evaluate(0,0,[0,0])
    except ValueError:pass
    else:raise AssertionError('same-location independent-error query accepted')
    # MC shares the C++ MEC algorithm, but independently samples the conditional joint prior.
    sim=json.loads(native(0,0,'mc',*q,20000,20260913))
    sim['J_zscore']=(sim['J_mean']-north['J'])/sim['J_se']
    sim['P_zscore']=(sim['P_finish']-north['P_finish'])/sim['P_finish_se']
    assert sim['invalid']==0 and sim['max_truth_outside']<1e-5
    assert abs(sim['J_zscore'])<4 and abs(sim['P_zscore'])<4,sim
    report['q2_joint_prior_mc']=sim
    # Independent construction uses radial intervals and finite support circles.
    geometries=[]
    cases=[(0,0,[700,0],0,0),(1700,0,[-930,0],2,0),
           (0,0,q,1,math.atan2(-q[1],700-q[0])),
           (1200,30,[458.35,275.45],1,math.atan2(-275.45,400-458.35))]
    for a,b,p,kind,theta in cases:
        g=json.loads(native(a,b,'geometry',*p,kind,theta))
        points=independent_points(a,b,p,kind,theta,n=16001)
        assert len(points)>0
        dirs=np.c_[np.cos(np.arange(64)*math.pi/32),np.sin(np.arange(64)*math.pi/32)]
        v=points[np.unique([int(np.argmax(points@u)) for u in dirs])]
        lower=exact_finite_radius(v);upper=g['radius_upper']
        outside=float(np.max(np.linalg.norm(points-np.array(g['center']),axis=1))-upper)
        assert outside<2e-5 and upper>=lower-2e-5
        geometries.append({'a':a,'beta_deg':b,'kind':kind,'q_internal':p,'sample_count':len(points),'lower_radius_m':lower,'upper_radius_m':upper,'gap_m':upper-lower,'max_sample_outside_m':outside})
    report['q2_independent_geometry']=geometries
    report.update(status='PASS',elapsed_s=time.monotonic()-start,
                  versions={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.suffix in ('.py','.cpp','.hpp') and '__pycache__' not in p.parts},
                  limits='有限几何采样、积分精度递增和独立抽样是数值核验；不构成连续全局最优或物理实验验证。')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'status':'PASS','q1_random_observations':60,'q1_projection_cases':200,'q2_reference_points':len(convergence),'q2_mc_samples':sim['n'],'elapsed_s':report['elapsed_s']},ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args().out)
