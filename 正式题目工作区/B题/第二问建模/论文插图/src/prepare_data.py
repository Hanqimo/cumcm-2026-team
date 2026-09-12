"""Compute figure data from preserved solvers, including continuous angular bounds."""
from pathlib import Path
import csv,json,subprocess,concurrent.futures,hashlib,time,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
DATA=ROOT/'data';BUILD=ROOT/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    DATA.mkdir(parents=True,exist_ok=True);BUILD.mkdir(exist_ok=True)
    start=time.time();source=BASE/'worstcase/src/worst_solver.cpp'
    contract=json.loads((ROOT/'input_contract.json').read_text())
    for name,digest in contract.items():
        assert sha(BASE/name)==digest,f'Source changed: {name}; review the figure inputs first.'
    text=source.read_text();assert text.count('int main(int argc,char**argv)')==1
    # Keep the computational core verbatim; the old CLI is unused by this driver.
    (ROOT/'src/worst_backend.hpp').write_text(text.split('int main(int argc,char**argv)')[0])
    exe=BUILD/'figure_backend'
    subprocess.run(['clang++','-std=c++17','-O3',str(ROOT/'src/figure_backend.cpp'),'-o',str(exe)],check=True)
    points=[(x,y) for y in range(400,701,2) for x in range(800,1041,2)]
    def work(k):
        p=DATA/f'heatmap_part{k}_input.csv';out=DATA/f'heatmap_part{k}.csv'
        with p.open('w') as f:
            w=csv.writer(f);w.writerow(['x','y']);w.writerows(points[k::3])
        subprocess.run([str(exe),'batch',str(p),str(out),'3'],check=True)
        return list(csv.DictReader(out.open()))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=sum(list(pool.map(work,range(3))),[])
    rows.sort(key=lambda r:(float(r['y']),float(r['x'])))
    with (DATA/'heatmap.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    comparison=json.loads((BASE/'worstcase/runs/R001/comparison.json').read_text())
    qe=comparison['results']['expected']['q'];qw=comparison['results']['minimax']['q']
    subprocess.run([str(exe),'curve',*map(str,qe+qw),str(DATA/'branch_curve.csv')],check=True)
    # Independent ray-interval polygons for the explanatory geometry.
    A=math.pi/180;q=np.array(qw);theta=comparison['results']['minimax']['independent_controlling_pairs']['normal']['theta']
    polygons={}
    for kind in ['normal','no_signal']:
        lows=[];highs=[]
        for phi in np.linspace(-A,A,2401):
            u=np.array([math.cos(phi),math.sin(phi)]);b=float(u@q)
            cuts=[5.,1500.]
            for rad in ([5,1500] if kind=='normal' else [1000]):
                disc=b*b+rad*rad-float(q@q)
                if disc>=0:cuts.extend([b-math.sqrt(disc),b+math.sqrt(disc)])
            if kind=='normal':
                for t in [theta-A,theta+A]:
                    v=np.array([math.cos(t),math.sin(t)]);den=u[0]*v[1]-u[1]*v[0]
                    if abs(den)>1e-14:cuts.append((q[0]*v[1]-q[1]*v[0])/den)
            elif abs(b)>1e-14:cuts.append(float(q@q)/(2*b))
            cuts=sorted(set(x for x in cuts if 5-1e-8<=x<=1500+1e-8))
            valid=[]
            for lo,hi in zip(cuts[:-1],cuts[1:]):
                r=(lo+hi)/2;g=r*u;d=float(np.linalg.norm(g-q))
                if kind=='normal':
                    diff=math.remainder(math.atan2(g[1]-q[1],g[0]-q[0])-theta,2*math.pi)
                    ok=5<d<=1500 and abs(diff)<=A+1e-12
                else:ok=d>max(1000,r)
                if ok:valid.append((lo,hi))
            assert len(valid)<=1,'This figure expects one radial interval per ray.'
            if valid:lows.append((u*valid[0][0]).tolist());highs.append((u*valid[0][1]).tolist())
        polygons[kind]=lows+highs[::-1]
    geometry={'q_E':qe,'q_W':qw,'normal_theta':theta,'polygons':polygons,'control':comparison['results']['minimax']['independent_controlling_pairs']}
    (DATA/'geometry.json').write_text(json.dumps(geometry,indent=2))
    summary={'grid_box':[800,1040,400,700],'grid_step_m':2,'grid_points':len(rows),'worst_angle_bound_max_gap_m':max(float(r['worst_upper'])-float(r['worst_lower']) for r in rows),'expected_integration_level':3,'source_hashes':{str(p.relative_to(BASE)):sha(p) for p in [source,BASE/'src/solver.cpp',BASE/'worstcase/runs/R001/comparison.json']},'elapsed_seconds':time.time()-start}
    (DATA/'preparation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
