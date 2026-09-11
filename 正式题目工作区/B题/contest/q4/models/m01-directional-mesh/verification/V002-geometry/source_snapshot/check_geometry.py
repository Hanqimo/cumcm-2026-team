"""Independent GEOS checks of continuous search and optical covers."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

MODEL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODEL/'src'))
from directional_geometry import DirectionalMesh, DirectionalTrack


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    mesh=DirectionalMesh()
    union=unary_union([Polygon(mesh.points[t]) for t in mesh.triangles])
    a=(np.arange(3600)+.5)*math.pi/1800
    outer=Polygon(np.column_stack([np.cos(a),np.sin(a)])*1800/math.cos(math.pi/3600))
    missing=outer.difference(union).area
    assert missing<1e-8
    max_edge=max(math.dist(mesh.points[i],mesh.points[j]) for t in mesh.triangles for i in t for j in t)
    assert max_edge<1000
    rng=np.random.default_rng(48112);checked=0;max_excess=0.
    for k in range(120):
        g=rng.uniform(-800,800,2);emission=rng.uniform(0,2*math.pi)
        track=DirectionalTrack(1)
        for angle in emission+np.array([-1.2,-.2,.8]):
            s=g+rng.uniform(60,999)*np.array([math.cos(angle),math.sin(angle)])
            a=math.degrees(math.atan2(g[1]-s[1],g[0]-s[0]))
            result=dict(measure_result='direction',svd_deg=round((a+(-1 if k%2 else 1))%360,2)%360)
            track.update(s,result)
            excess=Polygon(track.poly).distance(Point(g));max_excess=max(max_excess,excess)
            assert excess<=1e-5
            checked+=1
        before=track.poly.copy()
        track.update(g-10*np.array([math.cos(emission),math.sin(emission)]),dict(measure_result='no_signal'))
        assert np.array_equal(before,track.poly),'Backside loss must not delete position geometry'
    # Optical cover uses inscribed 19.49 m disks, independently of cell axes or
    # the clipping routine. A polygonal disk is strictly inside the 20 m disk.
    optical=[]
    for angle in [0.,43.,179.99,270.]:
        t=DirectionalTrack(1);t.update((0.,0.),dict(measure_result='direction',svd_deg=angle))
        cells=t.optical_cover();p=t.poly
        disks=[Point(q).buffer(19.49,quad_segs=64) for q in cells]
        difference=Polygon(p).difference(unary_union(disks)).area
        assert difference<1e-5,(angle,difference)
        optical.append(dict(bearing_deg=angle,cells=len(cells),uncovered_area_m2=difference))
    # A nearby point must not count as the exact mesh vertex.
    mesh.add_negative(1,mesh.points[0]+[1e-8,0]);assert not mesh.negative[1,0]
    result=dict(mesh_vertices=len(mesh.points),mesh_triangles=len(mesh.triangles),
                outside_arena_vertices=int(np.sum(np.linalg.norm(mesh.points,axis=1)>1800)),
                circumscribed_arena_polygon_missing_area_m2=missing,max_triangle_edge_m=max_edge,
                positive_region_checks=checked,max_true_point_excess_m=max_excess,
                backside_negative_region_checks=120,optical_covers=optical,
                optical_square_radius_m=13*math.sqrt(2),exact_vertex_identity_check=True)
    snap=args.output/'source_snapshot';snap.mkdir();hashes={}
    for f in list((MODEL/'src').glob('*.py'))+[Path(__file__)]:
        shutil.copy2(f,snap/f.name);hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
    result['source_sha256']=hashes
    (args.output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
