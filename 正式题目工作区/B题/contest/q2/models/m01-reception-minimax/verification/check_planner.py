"""Small integration check for the generic observable-input planner."""
from pathlib import Path
import sys,json,hashlib
from datetime import datetime,timezone
MODEL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(MODEL/'src'))
from planner import plan_next_observation


def main():
    out=MODEL/'verification/V03';out.mkdir(parents=True,exist_ok=False)
    contexts=[{'sensor':[0.,0.],'theta':0.,'budget':500.},
      {'sensor':[1600.,0.],'theta':0.,'budget':500.},
      {'sensor':[0.,1600.],'theta':45.,'budget':250.},
      {'sensor':[0.,0.],'theta':0.,'budget':1.}]
    result=[]
    for context in contexts:
        value=plan_next_observation(**context)
        if context['budget']==1:assert value['status']=='empty_candidate_grid'
        else:
            assert value['status']=='recommended_finite_grid'
            assert min(value['constraint_margins_m'].values())>=-1e-7
        result.append({'input':context,'output':value})
    root=MODEL.parents[3]
    paths=[Path(__file__),MODEL/'src/planner.py',MODEL/'src/second_point.py',root/'contest/q1/models/m01-bounded-bearing/src/bearing_geometry.py']
    snap=out/'source_snapshot';snap.mkdir()
    for p in paths:(snap/p.name).write_bytes(p.read_bytes())
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'status':'passed','utc':datetime.now(timezone.utc).isoformat(),
      'purpose':'generic observable-input API integration, separate grid from Q2-R002',
      'command':'python -X utf8 contest/q2/models/m01-reception-minimax/verification/check_planner.py',
      'uncommitted_source':True,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2),encoding='utf-8')
    print(json.dumps([{'input':x['input'],'status':x['output']['status'],'point':x['output'].get('point'),
      'radius_upper_m':x['output'].get('radius_upper_m')} for x in result],indent=2))


if __name__=='__main__':main()
