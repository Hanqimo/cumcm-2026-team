"""Cross-evaluation and independent geometry of the controlling feedbacks."""
import csv, json, math, subprocess, importlib.util, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
RUN=ROOT/'runs/R001';VERIFY=ROOT/'verification';A=math.pi/180
spec=importlib.util.spec_from_file_location('independent_ray',BASE/'src/verify_geometry.py')
ray=importlib.util.module_from_spec(spec);spec.loader.exec_module(ray)

def csv_call(exe,*args):
    lines=subprocess.check_output([str(exe),*map(str,args)],text=True).splitlines()
    return {k:float(v) for k,v in next(csv.DictReader(lines)).items()}

def norm(v):return math.hypot(*v)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def unit(a):return np.array([math.cos(a),math.sin(a)])

def controlling_pairs(q):
    # Independent line/ray construction, not the C++ primitive intersections.
    q=np.array(q);far=1500*unit(-A)
    theta=math.atan2(*(far-q)[::-1])-A
    v=unit(theta-A);u=unit(A);s=cross(q,v)/cross(u,v);opposite=s*u
    near=5*unit(A);u0=unit(-A);b=float(q@u0)
    t=b-math.sqrt(b*b+1000**2-float(q@q));outer=t*u0
    return {'normal':{'theta':theta%(2*math.pi),'points':[far.tolist(),opposite.tolist()],
                        'radius':norm(far-opposite)/2,'center':((far+opposite)/2).tolist()},
            'no_signal':{'points':[near.tolist(),outer.tolist()],
                         'radius':norm(near-outer)/2,'center':((near+outer)/2).tolist()}}

def main():
    best=json.loads((RUN/'best_search.json').read_text());old=json.loads((BASE/'results/radius/best.json').read_text())
    points={'minimax':[best['x'],best['y']], 'expected':[old['x'],old['y']],
            'minimax_rounded_2dp':[round(best['x'],2),round(best['y'],2)],
            'minimax_rounded_1dp_tangent':[969.3,497.8]}
    results={};checks=[];convergence=[]
    for name,q in points.items():
        cert=csv_call(ROOT/'worst_solver','cert',*q,1e-5)
        assert cert['angle_bound_complete']==1
        e5=csv_call(ROOT/'expected_solver','eval',*q,5);e6=csv_call(ROOT/'expected_solver','eval',*q,6)
        result={'q':q,'strict_worst':cert,'uniform_prior_expectation':e6}
        results[name]=result
        convergence.append({'name':name,'expected_radius_level5':e5['E_radius_loss'],
            'expected_radius_level6':e6['E_radius_loss'],
            'expected_radius_difference':abs(e6['E_radius_loss']-e5['E_radius_loss']),
            'probability_total_error':abs(sum(e6[k] for k in ['P_H','P_N','P_A'])-1),
            'worst_radius_gap_m':cert['worst_upper']-cert['worst_lower']})
        if name not in ['minimax','expected']:continue
        pairs=controlling_pairs(q);result['independent_controlling_pairs']=pairs
        for kind,label in [(1,'normal'),(2,'no_signal')]:
            pair=pairs[label];theta=pair.get('theta',0)
            ps=ray.ray_points(q,kind,theta,n=40001)
            center=np.array(pair['center']);radius=pair['radius']
            residual=float(np.linalg.norm(ps-center,axis=1).max()-radius)
            assert residual<1e-6,(name,label,residual)
            cpp_radius=cert['normal_lower'] if kind==1 else cert['no_signal_upper']
            assert abs(cpp_radius-radius)<2e-5,(name,label,cpp_radius,radius)
            checks.append({'name':name,'branch':label,'independent_radius':radius,
                'cpp_radius':cpp_radius,'sample_count':len(ps),'max_sample_outside_m':residual,
                'support_pair':pair['points'],'method':'analytic opposing rays plus independent polar radial intervals'})
        # Broad normal-angle cases: reuse neither boundary arcs nor C++ interval roots.
        pg=np.array([r*unit(t) for r in np.linspace(5.01,1500,25) for t in np.linspace(-A,A,13)])
        ph=np.unwrap(np.arctan2(pg[:,1]-q[1],pg[:,0]-q[0]))
        for theta in np.linspace(float(ph.min())-A,float(ph.max())+A,25):
            ps=ray.ray_points(q,1,theta,n=8001)
            if not len(ps):continue
            geo=json.loads(subprocess.check_output([str(ROOT/'worst_solver'),'normal',*map(str,q),str(theta)],text=True))
            residual=float(np.linalg.norm(ps-np.array(geo['center']),axis=1).max()-geo['radius'])
            assert residual<1e-5,(name,theta,residual)
            checks.append({'name':name,'branch':'normal-angle-grid','theta':theta,'sample_count':len(ps),'max_sample_outside_m':residual})
        reflection=csv_call(ROOT/'worst_solver','cert',q[0],-q[1],1e-5)
        assert abs(reflection['worst_lower']-cert['worst_lower'])<1e-6
        result['reflection']=reflection
    a=results['minimax'];b=results['expected']
    wa=sum(a['strict_worst'][k] for k in ['worst_lower','worst_upper'])/2
    wb=sum(b['strict_worst'][k] for k in ['worst_lower','worst_upper'])/2
    ea=a['uniform_prior_expectation']['E_radius_loss'];eb=b['uniform_prior_expectation']['E_radius_loss']
    comparison={'worst_radius_reduction_m_estimate':wb-wa,'worst_radius_reduction_percent_estimate':100*(wb-wa)/wb,
        'expected_radius_increase_m':ea-eb,'expected_radius_increase_percent':100*(ea-eb)/eb,
        'candidate_distance_m':norm(np.array(a['q'])-np.array(b['q'])),
        'uniform_prior_is_evaluation_reference_not_minimax_assumption':True}
    (RUN/'comparison.json').write_text(json.dumps({'results':results,'comparison':comparison},ensure_ascii=False,indent=2))
    (VERIFY/'independent_geometry.json').write_text(json.dumps(checks,indent=2))
    (VERIFY/'convergence.json').write_text(json.dumps(convergence,indent=2))
    with (RUN/'comparison.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['model','x','y','worst_lower_m','worst_upper_m','mean_radius_m','no_signal_probability','normal_worst_lower_m','no_signal_radius_m','original_site_localization_probability'])
        for name,r in results.items():
            s=r['strict_worst'];e=r['uniform_prior_expectation']
            w.writerow([name,*r['q'],s['worst_lower'],s['worst_upper'],e['E_radius_loss'],e['P_N'],s['normal_lower'],s['no_signal_upper'],e['P_loc']])
    print(json.dumps({'comparison':comparison,'independent_cases':len(checks),'max_sample_outside_m':max(c['max_sample_outside_m'] for c in checks),'convergence':convergence},indent=2),flush=True)

if __name__=='__main__':main()
