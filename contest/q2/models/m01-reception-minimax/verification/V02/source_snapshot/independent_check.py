"""V02: independent polygon construction/support checks, reading-bin coverage.

Does not rerun spatial optimization. Uses Q1 line enumeration/LP instead of Q2
incremental clipping. Uses original atan2 inequalities to check reading bins.
"""
from pathlib import Path
import sys,json,hashlib,subprocess,platform
from datetime import datetime,timezone
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linprog

MODEL=Path(__file__).resolve().parents[1]
ROOT=MODEL.parents[3]
sys.path.insert(0,str(MODEL/'src'))
from second_point import (first_region,posterior,worst_radius_upper,bearing,
    angle_difference,unit,in_candidate,candidate_margins)
from bearing_geometry import halfplane_region,wedge,diameter,enclosing_circle


def main():
    dest=MODEL/'verification/V02'
    dest.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(20260911)
    poly=first_region();hull=ConvexHull(poly)
    aa=hull.equations[:,:2];bb=-hull.equations[:,2]
    q=np.array([257.51903745502716,428.5836503510561])
    max_support_error=0.;max_radius_error=0.;max_bin_angle_violation=0.;tests=0
    for _ in range(40):
        x=rng.uniform(5.1,1499.9)*unit(rng.uniform(-1,1))
        reading=(bearing(x,q)+rng.uniform(-1,1))%360
        clipped=posterior(poly,q,reading)
        wa,wb=wedge(q,reading)
        A=np.vstack([aa,wa]);b=np.r_[bb,wb]
        alternate=halfplane_region(A,b)
        assert len(clipped)>0 and alternate.status=='polygon'
        for phi in rng.uniform(0,360,5):
            u=unit(phi)
            lp=linprog(-u,A_ub=A,b_ub=b,bounds=[(None,None)]*2,method='highs')
            assert lp.success
            max_support_error=max(max_support_error,abs(-lp.fun-np.max(clipped@u)))
        max_radius_error=max(max_radius_error,abs(enclosing_circle(clipped)[1]-enclosing_circle(alternate.vertices)[1]))
        # Artificial reading bin [reading-delta, reading+delta], move its center
        # away from this actual reading. Direct angles validate every vertex.
        delta=.025;center=reading+rng.uniform(-delta,delta)
        direct_angles=np.array([bearing(v,q) for v in clipped])
        max_bin_angle_violation=max(max_bin_angle_violation,float(np.max(np.abs(angle_difference(direct_angles,center)))-1-delta))
        tests+=1
    assert max_support_error<1e-6 and max_radius_error<1e-6 and max_bin_angle_violation<1e-7
    right=worst_radius_upper(poly,q,bin_width_deg=.05)['radius_upper_m']
    left=worst_radius_upper(poly,q*[1,-1],bin_width_deg=.05)['radius_upper_m']
    assert abs(right-left)<1e-6
    # The chosen locations remain feasible over an explicitly tested threshold range.
    import csv
    with (MODEL/'runs/R002/selected_points.csv').open(encoding='utf-8-sig') as f:
        points=list(csv.DictReader(f))
    for row in points:
        p=[float(row['a_m']),float(row['b_m'])]
        for h in [5,20,50,100]:assert in_candidate(p,budget=float(row['budget_m']),lateral_min=h)
    # Float rounding to three decimals can slightly exceed the travel budget;
    # export full precision and check actual original constraints after any rounding.
    result={'status':'passed','random_seed':20260911,'posterior_cases':tests,
      'support_max_difference_m':max_support_error,'radius_max_difference_m':max_radius_error,
      'reading_bin_max_violation_deg':max_bin_angle_violation,'reflection_difference_m':abs(right-left),
      'scope':'Independent representations for construction; analytical proof, not samples, supports continuous reception guarantee'}
    (dest/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    files=[Path(__file__),MODEL/'src/second_point.py',ROOT/'contest/q1/models/m01-bounded-bearing/src/bearing_geometry.py']
    snap=dest/'source_snapshot';snap.mkdir()
    for p in files:(snap/p.name).write_bytes(p.read_bytes())
    manifest={'validation':'Q2-V02','upstream_run':'Q2-R002','utc':datetime.now(timezone.utc).isoformat(),
      'command':'python -X utf8 contest/q2/models/m01-reception-minimax/verification/independent_check.py',
      'base_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'uncommitted_source':True,'python':platform.python_version(),'seed':20260911,
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
