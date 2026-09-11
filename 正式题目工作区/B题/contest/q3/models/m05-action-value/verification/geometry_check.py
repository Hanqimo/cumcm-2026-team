"""Direct-distance independent checks of failed-clear outer-set preservation."""
import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,Point
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from action_value import OpticalTrack
from bearing_geometry import enclosing_circle


def main():
    rng=np.random.default_rng(15001);checks=0;holes=0;split=0
    for k in range(120):
        # Thin, broad, translated, and near-tangent rectangles.
        center=rng.uniform(-1800,1800,2);half=np.array([rng.uniform(15,80),rng.uniform(.05,30)])
        t=OpticalTrack(1);t.poly=center+half*np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
        t.sync_region();original=t.feasible
        q=center+rng.uniform(-.8,.8,2)*half
        points=center+rng.uniform(-1,1,(300,2))*half
        outside=points[np.linalg.norm(points-q,axis=1)>20]
        t.exclude_clear(q)
        for p in outside:
            assert t.feasible.distance(Point(p))<1e-8
            assert np.linalg.norm(p-t.center)<=t.radius+1e-7
            checks+=1
        assert t.feasible.difference(original).area<1e-7
        if t.feasible.geom_type=='MultiPolygon':split+=1
        elif t.feasible.interiors:holes+=1
    result=dict(seed=15001,rectangles=120,direct_membership_checks=checks,
                cases_with_holes=holes,disconnected_cases=split,passed=True,
                excluded_radius_m=19.999,polygon_sides=64)
    print(json.dumps(result,indent=2))
    out=ROOT/'verification/geometry-v1.json'
    if out.exists():raise FileExistsError(out)
    out.write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
