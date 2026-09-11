"""Independent Qhull Voronoi vertices plus a Lipschitz boundary upper bound."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
from scipy.spatial import Voronoi
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from voronoi_coverage import covering_radius


def main():
    out=ROOT/'verification/continuous-cover-v1';out.mkdir(exist_ok=False)
    rng=np.random.default_rng(261109);rows=[]
    special=[([[0,0]],1800.),([[100,0]],1900.),([[-500,0],[500,0]],math.hypot(1800,500)),
        (1300*np.column_stack([np.cos(np.arange(6)*math.pi/3),np.sin(np.arange(6)*math.pi/3)]),1300.)]
    for p,expected in special:assert abs(covering_radius(p)[0]-expected)<1e-6
    n_boundary=16384;angle=np.arange(n_boundary)*2*math.pi/n_boundary
    boundary=1800*np.column_stack([np.cos(angle),np.sin(angle)])
    bound=math.pi*1800/n_boundary
    for case in range(160):
        p=rng.uniform(-2200,2200,(rng.integers(4,18),2))
        value,witness=covering_radius(p)
        vertices=Voronoi(p).vertices
        vertices=vertices[np.linalg.norm(vertices,axis=1)<=1800]
        interior=float(np.max(np.min(np.linalg.norm(vertices[:,None,:]-p[None,:,:],axis=2),axis=1))) if len(vertices) else 0.
        boundary_max=0.
        for chunk in np.array_split(boundary,8):
            boundary_max=max(boundary_max,float(np.max(np.min(np.linalg.norm(chunk[:,None,:]-p[None,:,:],axis=2),axis=1))))
        lower=max(interior,boundary_max);upper=max(interior,boundary_max+bound)
        assert lower-1e-6<=value<=upper+1e-6,(case,lower,value,upper)
        assert abs(np.min(np.linalg.norm(p-witness,axis=1))-value)<1e-7
        rows.append(dict(case=case,sites=len(p),computed=value,independent_lower=lower,independent_upper=upper))
    result=dict(seed=261109,random_cases=len(rows),analytic_special_cases=len(special),boundary_samples_per_case=n_boundary,
        boundary_lipschitz_upper_gap_m=bound,method='Independent scipy/Qhull Voronoi vertices; uniform boundary samples plus distance-function Lipschitz upper bound',
        source_sha256=hashlib.sha256((ROOT/'src/voronoi_coverage.py').read_bytes()).hexdigest(),cases=rows)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Validated',len(rows),'random and',len(special),'analytic cases')


if __name__=='__main__':main()
