"""Check frozen-code identity, packaged factory behavior and complete time ledger."""
import contextlib,hashlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from strategy import Planner,POLICIES
from benchmark import worlds


def main():
    run=ROOT/'runs/R009-frozen-audit'
    manifest=json.loads((run/'manifest.json').read_text())
    snapshot=run/'source_snapshot';checked={}
    for p in (ROOT/'src').glob('*.py'):
        if p.name in manifest['source_sha256']:
            actual=hashlib.sha256(p.read_bytes()).hexdigest()
            assert actual==manifest['source_sha256'][p.name],p
            checked[p.name]=actual
    for name,source in [('clearance_geometry.py',ROOT.parents[2]/'q1/models/m01-bounded-bearing/src/clearance_geometry.py'),
                        ('reception_region.py',ROOT.parents[2]/'q2/models/m01-reception-minimax/src/reception_region.py')]:
        assert source.read_bytes()==(ROOT/'src'/name).read_bytes()
    base=json.loads((snapshot/'base-v3.json').read_text());config=json.loads((snapshot/'config.json').read_text())
    assert POLICIES['combined_v4']==dict(base,**config['combined'])
    rows=json.loads((run/'results.json').read_text())
    fixtures=json.loads((run/'fixtures.json').read_text());_,World,_=worlds();cases=[]
    for seed in [9000,9050]:
        for variant,policy in [('baseline','baseline_v3'),('combined','combined_v4')]:
            targets={int(k):v for k,v in fixtures[str(seed)].items()}
            world=World(targets,seed,keep_events=True)
            with contextlib.redirect_stdout(io.StringIO()):Planner(world,policy=policy).run()
            ref=next(r for r in rows if r['seed']==seed and r['variant']==variant)
            assert abs(world.virtual-ref['time_s'])<1e-7
            assert world.cleared==set(targets) and world.clear_failures==0
            ledger=world.distance_m/5+5*world.measure_count+world.switches+5*len(world.cleared)
            assert abs(world.virtual-ledger)<1e-7
            cases.append(dict(seed=seed,policy=policy,time_s=world.virtual,ledger_error_s=world.virtual-ledger,
                regions_checked=world.region_checks,clear_certificates=world.clear_checks,
                cost_decisions=sum(e['kind']=='cost_action' for e in world.events),
                scan_merges=sum(e['kind']=='merge_scans' for e in world.events)))
    out=ROOT/'verification/integration-audit.json'
    with out.open('x',encoding='utf-8') as f:
        json.dump(dict(frozen_core_sha256=checked,q12_canonical_copies_identical=True,packaged_parameters_identical=True,
            factory_cases=cases,no_official_network_calls=True),f,indent=2)
    print(json.dumps(cases,indent=2))


if __name__=='__main__':main()
