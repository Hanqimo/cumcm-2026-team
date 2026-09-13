"""复现论文 200 组最近保证清除位置检验，保留原随机序列。"""
from pathlib import Path
import json
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import minimize
from .bearing_geometry import enclosing_circle
from .clearance_geometry import nearest_clear_point


def segment_clear_point(v,c,p):
    if np.max(np.linalg.norm(v-p,axis=1))<=19.5:return p.copy()
    low,high=0.,1.
    for _ in range(45):
        t=(low+high)/2;q=c+t*(p-c)
        if np.max(np.linalg.norm(v-q,axis=1))<=19.5:low=t
        else:high=t
    return c+low*(p-c)


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
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
        oldq=segment_clear_point(v,center,p)
        saved=float(np.linalg.norm(oldq-p)-np.linalg.norm(q-p))
        assert saved>=-1e-6
        rows.append(dict(case=i,saved_m=saved,independent_objective_error_m=float(distance_error),solver_success=bool(solution.success),solver_message=solution.message))
    report={'cases':200,'seed':712233,'max_distance_difference_m':max(r['independent_objective_error_m'] for r in rows),
            'mean_saved_m':float(np.mean([r['saved_m'] for r in rows])),
            'max_saved_m':max(r['saved_m'] for r in rows),
            'slsqp_success_count':sum(r['solver_success'] for r in rows),
            'note':'SLSQP status is reported alongside objective/feasibility checks; all comparisons use synthetic geometry.'}
    (out/'cases.json').write_text(json.dumps(rows,indent=2));(out/'report.json').write_text(json.dumps(report,indent=2))
    return report
