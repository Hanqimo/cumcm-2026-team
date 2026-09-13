"""复现论文第一问的 60 组观测几何检验，随机种子及抽样顺序与原记录一致。"""
from pathlib import Path
import json,time
import numpy as np
from scipy.optimize import linprog,minimize
from .bearing_geometry import (observations_halfplanes,halfplane_region,summarize_region,
    diameter,enclosing_circle,bearing,angle_difference,unit,wedge)


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    start = time.perf_counter()
    seed = 20260910
    rng = np.random.default_rng(seed)
    checks = []
    def check(name, condition, details=None):
        checks.append(dict(name=name, passed=bool(condition), details=details))
        if not condition:
            raise AssertionError(f'{name}: {details}')

    # A triangle realizable by THREE directed 2-degree bearing wedges.
    L = 38.
    triangle = np.array([[0, 0], [L, 0], [L/2, L*np.sqrt(3)/2]])
    observations = []
    for i in range(3):
        u = (triangle[(i+1)%3] - triangle[i]) / L
        s = triangle[i] - 1000*u
        observations.append(dict(position=s.tolist(), bearing_deg=(np.rad2deg(np.arctan2(u[1],u[0]))+1)%360))
    A, b = observations_halfplanes(observations)
    reg = halfplane_region(A,b)
    tri = summarize_region(reg)
    check('realizable_triangle_diameter', abs(tri['diameter_m']-L)<1e-7, tri)
    check('realizable_triangle_radius', abs(tri['cover_radius_m']-L/np.sqrt(3))<1e-7)
    target = triangle.mean(axis=0)
    for o in observations:
        check('triangle_direct_angle_consistency', abs(angle_difference(bearing(target,o['position']),o['bearing_deg']))<=1+1e-10)
        check('triangle_physical_reception', 5 < np.linalg.norm(target-o['position']) < 1500)
    check('diameter_38_not_clearable', tri['diameter_m']<40 and tri['cover_radius_m']>20)
    tri['observations'] = observations
    tri['true_target_for_consistency'] = target.tolist()
    (out/'counterexample.json').write_text(json.dumps(tri,ensure_ascii=False,indent=2),encoding='utf-8')

    # Orthogonal central bearings: independent slope-line construction below.
    symmetric = [dict(position=[-1000,0],bearing_deg=0),dict(position=[0,-1000],bearing_deg=90)]
    A0,b0=observations_halfplanes(symmetric)
    sy = summarize_region(halfplane_region(A0,b0))
    # It is not exactly a diamond about the origin: solve all four lines by hand
    # in slope form (independent of the normal/LP representation).
    t=np.tan(np.deg2rad(1.0)); expected=[]
    for f in [-1,1]:
        for g in [-1,1]:
            expected.append(np.linalg.solve([[ -f*t,1],[1,-g*t]],[f*t*1000,g*t*1000]))
    check('orthogonal_tangent_construction', abs(diameter(expected)[0]-sy['diameter_m'])<1e-7)
    (out/'orthogonal_example.json').write_text(json.dumps(sy,indent=2),encoding='utf-8')

    # Empty, unbounded, line and point must not be hidden by a finite box.
    A1,b1=wedge([0,0],0)
    check('single_wedge_unbounded',halfplane_region(A1,b1).status=='unbounded')
    A2,b2=wedge([-10,0],180)
    check('incompatible_wedges_empty',halfplane_region(np.vstack([A1,A2]),np.r_[b1,b2]).status=='empty')
    basic=np.array([[1,0],[-1,0],[0,1],[0,-1]])
    check('segment_classification',halfplane_region(basic,[1,0,0,0]).status=='segment')
    check('point_classification',halfplane_region(basic,[0,0,0,0]).status=='point')

    # Direct atan2 membership independently validates angular signs and wrapping.
    max_membership_mismatch=0
    for theta in [0, .2, 89.8,90,179.9,270,359.8]:
        s=rng.uniform(-2000,2000,2)
        angles=theta+rng.uniform(-3,3,500)
        points=s+rng.uniform(5,1500,(500,1))*np.column_stack((np.cos(np.deg2rad(angles)),np.sin(np.deg2rad(angles))))
        aa,bb=wedge(s,theta)
        direct=np.abs(angle_difference(angles,theta))<=1
        linear=np.all(points@aa.T<=bb+1e-9,axis=1)
        max_membership_mismatch+=int(np.count_nonzero(direct!=linear))
    check('atan2_vs_halfplanes_3500_points',max_membership_mismatch==0,max_membership_mismatch)

    support_error=0.; circle_error=0.; containment_error=0.; equivariance_error=0.
    for k in range(60):
        x=rng.uniform(-700,700,2)
        count=int(rng.integers(3,9))
        angles=np.arange(count)*360/count+rng.uniform(-12,12,count)
        sensors=x+rng.uniform(150,1450,(count,1))*np.array([unit(a) for a in angles])
        obs=[dict(position=s.tolist(),bearing_deg=(bearing(x,s)+rng.uniform(-1,1))%360) for s in sensors]
        aa,bb=observations_halfplanes(obs)
        r=halfplane_region(aa,bb)
        check('random_bounded_region',r.status=='polygon')
        containment_error=max(containment_error,float(np.max(aa@x-bb)))
        for a in rng.uniform(0,360,10):
            u=unit(a)
            lp=linprog(-u,A_ub=aa,b_ub=bb,bounds=[(None,None)]*2,method='highs')
            support_error=max(support_error,abs(-lp.fun-np.max(r.vertices@u)))
        c,radius,_=enclosing_circle(r.vertices)
        # Independent convex norm epigraph minimization, scaled to unit geometry.
        center=r.vertices.mean(axis=0);scale=max(1.,np.max(np.linalg.norm(r.vertices-center,axis=1)))
        v=(r.vertices-center)/scale
        sol=minimize(lambda z:z[2],np.r_[np.zeros(2),2.],method='SLSQP',
          constraints={'type':'ineq','fun':lambda z:z[2]-np.linalg.norm(v-z[:2],axis=1)},
          bounds=[(None,None),(None,None),(0,None)],options={'ftol':1e-10,'maxiter':500})
        check('independent_circle_solver_status',sol.success,sol.message)
        circle_error=max(circle_error,abs(sol.x[2]*scale-radius))
        check('circle_vertex_coverage',np.max(np.linalg.norm(r.vertices-c,axis=1))<=radius+1e-8)
        check('diameter_circle_bounds',diameter(r.vertices)[0]/2<=radius+1e-7 and radius<=diameter(r.vertices)[0]/np.sqrt(3)+1e-7)
        rot=unit(37);R=np.array([[rot[0],-rot[1]],[rot[1],rot[0]]]);shift=np.array([12345.,-9876.])
        obs2=[dict(position=(R@np.array(o['position'])+shift).tolist(),bearing_deg=(o['bearing_deg']+37)%360) for o in obs]
        moved=halfplane_region(*observations_halfplanes(obs2))
        equivariance_error=max(equivariance_error,abs(diameter(moved.vertices)[0]-diameter(r.vertices)[0]))
    check('LP_support_vs_vertex_enumeration',support_error<1e-6,support_error)
    check('convex_optimization_vs_support_circle',circle_error<1e-5,circle_error)
    check('true_target_containment',containment_error<1e-7,containment_error)
    check('rotation_translation_invariance',equivariance_error<1e-6,equivariance_error)

    # More observations cannot enlarge an intersection.
    extra=dict(position=[800,400],bearing_deg=bearing([0,0],[800,400]))
    aa,bb=observations_halfplanes(symmetric+[extra]);more=summarize_region(halfplane_region(aa,bb))
    check('information_monotonicity',more['diameter_m']<=sy['diameter_m']+1e-8 and more['cover_radius_m']<=sy['cover_radius_m']+1e-8)

    report={'checks':checks,'passed':all(c['passed'] for c in checks),'random_cases':60,
            'seed':seed,'support_max_error_m':support_error,'circle_max_error_m':circle_error,
            'equivariance_error_m':equivariance_error,'elapsed_s':time.perf_counter()-start}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report
