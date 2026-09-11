"""Reproduce deterministic polar layouts; no scene or hidden source input."""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from directional_geometry import DirectionalMesh
from adaptive_cover import split_triangle
from bearing_geometry import outer_disk


def construct(ni,no,ri,ro):
    mesh=DirectionalMesh();arena=Polygon(outer_disk((0.,0.),1800.,360))
    points=np.vstack([[[0,0]],[[ri*math.cos(2*math.pi*i/ni),ri*math.sin(2*math.pi*i/ni)] for i in range(ni)],
                      [[ro*math.cos(2*math.pi*i/no),ro*math.sin(2*math.pi*i/no)] for i in range(no)]])
    def valid(cell):
        eligible=np.max(np.sum((points[:,None,:]-cell[None,:,:])**2,axis=2),axis=1)<=999.99**2
        if sum(eligible)<3:return False
        try:h=ConvexHull(points[eligible])
        except Exception:return False
        return np.max(cell@h.equations[:,:2].T+h.equations[:,2])<1e-8
    stack=[(mesh.points[t],0) for t in mesh.triangles];cells=[];levels={};failure=None
    while stack:
        tri,depth=stack.pop();poly=Polygon(tri).intersection(arena)
        if poly.is_empty or poly.area<1e-9:continue
        cell=np.array(poly.exterior.coords[:-1])
        if valid(cell):cells.append(cell.tolist());levels[depth]=levels.get(depth,0)+1
        elif not valid(np.array([poly.representative_point().coords[0]])) or depth>=7:
            failure=dict(point=list(poly.representative_point().coords[0]),level=depth);break
        else:stack.extend((t,depth+1) for t in split_triangle(tri,1))
    return dict(points=points.tolist(),cells=cells,levels=levels),failure


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    for name,ni,no in [('polar22',7,14),('polar25',8,16)]:
        data,failure=construct(ni,no,980,1850);assert failure is None
        original=json.loads((ROOT/'src'/f'{name}.json').read_text())
        # Exact coordinate equality checks the geometry file sent to the robot.
        assert data['points']==original['points'] and data['cells']==original['cells']
        (args.output/f'{name}.json').write_text(json.dumps(data))
        print(name,'reproduced',len(data['cells']),'cells')


if __name__=='__main__':main()
