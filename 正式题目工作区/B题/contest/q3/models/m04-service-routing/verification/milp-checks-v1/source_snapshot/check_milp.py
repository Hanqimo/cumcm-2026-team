"""Compare small covering-route MILPs with exhaustive visits/scans/permutations."""
import itertools,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from cover_milp import solve_cover_route


def main():
    out=ROOT/'verification/milp-checks-v1';out.mkdir(exist_ok=False)
    rng=np.random.default_rng(120712);rows=[]
    for case in range(20):
        p=rng.uniform(-1000,1000,(6,2));masks=rng.random((6,8))<.45
        for k in range(8):masks[rng.integers(6),k]=True
        mandatory={1,2};cost=12.;best=float('inf')
        for bits in range(1<<5):
            visits={0}|{j+1 for j in range(5) if bits>>j&1}
            if not mandatory.issubset(visits):continue
            scan_count=99
            for scans_bits in range(1<<6):
                scans={j for j in range(6) if scans_bits>>j&1}
                if not scans or not scans.issubset(visits):continue
                if np.all(np.any(masks[list(scans)],axis=0)):scan_count=min(scan_count,len(scans))
            if scan_count==99:continue
            for route in itertools.permutations(sorted(visits-{0})):
                path=(0,)+route
                length=sum(np.linalg.norm(p[a]-p[b])/5 for a,b in zip(path,path[1:]))
                best=min(best,length+cost*scan_count)
        answer=solve_cover_route(p,mandatory,masks,cost,time_limit=3.)
        assert answer is not None and abs(answer['cost']-best)<1e-6,(case,best,answer)
        rows.append(dict(case=case,enumerated_optimum=best,milp_cost=answer['cost'],reported_gap=answer['gap']))
    (out/'result.json').write_text(json.dumps(dict(seed=120712,cases=rows),indent=2),encoding='utf-8')
    print('20 exhaustive small-instance checks passed')


if __name__=='__main__':main()
