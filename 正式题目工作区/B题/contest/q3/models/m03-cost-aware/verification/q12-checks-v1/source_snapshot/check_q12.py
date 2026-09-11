"""Independent convex-solver and direct-distance checks of Q1/Q2 additions."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from clearance_geometry import nearest_clear_point
from reception_region import reception_violation
from legacy_strategy import Track
from bearing_geometry import enclosing_circle


def main():
    out=ROOT/'verification/q12-checks-v1';out.mkdir(exist_ok=False)
    rng=np.random.default_rng(712233)
    rows=[]
    for i in range(200):
        v=rng.normal(size=(rng.integers(3,14),2));v=v[ConvexHull(v).vertices]
        center,r,_=enclosing_circle(v);v=(v-center)*rng.uniform(5,19.4)/r+rng.uniform(-1000,1000,2)
        center,r,_=enclosing_circle(v);p=center+rng.normal(size=2)*300
        q=nearest_clear_point(v,p,19.5,center);assert q is not None
        vv=(v-center)/20;pp=(p-center)/20
        objective=lambda x:float(np.sum((x-pp)**2)/2)
        solution=minimize(objective,np.zeros(2),jac=lambda x:x-pp,method='SLSQP',
            constraints={'type':'ineq','fun':lambda x:(19.5/20)**2-np.sum((vv-x)**2,axis=1),
                         'jac':lambda x:2*(vv-x)},options={'ftol':1e-11,'maxiter':300})
        qp=solution.x*20+center
        assert np.max(np.linalg.norm(v-q,axis=1))<=19.5+1e-7
        distance_error=abs(np.linalg.norm(q-p)-np.linalg.norm(qp-p))
        assert distance_error<1e-4,(i,solution.message,distance_error)
        old=Track(1);old.poly=v;old.center=center;old.radius=r
        oldq=old.safe_clear_point(p)
        saved=float(np.linalg.norm(oldq-p)-np.linalg.norm(q-p))
        assert saved>=-1e-6
        rows.append(dict(case=i,saved_m=saved,independent_objective_error_m=float(distance_error)))
    # Independent pointwise test: sample convex combinations directly.
    gaps=[];tested=0
    for i in range(300):
        v=rng.uniform(-1800,1800,(12,2));v=v[ConvexHull(v).vertices]
        s=rng.uniform(-1800,1800,2);q=rng.uniform(-1800,1800,2)
        weights=rng.dirichlet(np.full(len(v),.25),4000);x=weights@v
        upper,witness=reception_violation(v,s,q)
        value=np.sum((x-q)**2,axis=1)-np.maximum(1000**2,np.sum((x-s)**2,axis=1))
        assert float(value.max())<=upper+1e-5
        actual=float(np.linalg.norm(witness-q)**2-max(1000**2,np.linalg.norm(witness-s)**2))
        assert abs(actual-upper)<1e-5
        gaps.append(float(upper-value.max()));tested+=len(x)
    poly=np.array([[200.,-1.],[1499.,-1.],[1499.,1.],[200.,1.]])
    s=np.zeros(2);q=np.array([550.,840.]);upper,witness=reception_violation(poly,s,q)
    old_allclose=float(np.max(np.linalg.norm(poly-q,axis=1)))
    assert np.linalg.norm(q)>1000 and old_allclose>1000 and upper<0
    example=dict(polygon=poly.tolist(),first_sensor=s.tolist(),new_point=q.tolist(),
        distance_from_first_m=float(np.linalg.norm(q)),max_distance_to_polygon_m=old_allclose,
        max_squared_violation_m2=upper,worst_witness=witness.tolist(),
        old_sufficient_tests_accept=False,new_region_test_accept=True)
    result=dict(q1_cases=len(rows),q1_mean_saved_m=float(np.mean([r['saved_m'] for r in rows])),
        q1_max_saved_m=max(r['saved_m'] for r in rows),q1_max_solver_objective_error_m=max(r['independent_objective_error_m'] for r in rows),
        q2_cases=len(gaps),q2_direct_points=tested,q2_example=example,
        source_sha256={n:hashlib.sha256((ROOT/'src'/n).read_bytes()).hexdigest() for n in ['clearance_geometry.py','reception_region.py']})
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'projection-cases.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
