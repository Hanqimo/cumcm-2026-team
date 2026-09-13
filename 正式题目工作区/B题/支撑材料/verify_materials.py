"""Read-only support-file verification. Never connects to the simulator."""
from pathlib import Path
import ast
import hashlib
import json

ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    sums=ROOT/'SHA256SUMS.json'
    if sums.exists():
        for name,wanted in read(sums)['files'].items():
            assert digest(ROOT/name)==wanted, f'Hash mismatch: {name}'
    for p in ROOT.rglob('*.py'):
        if '__pycache__' not in p.parts:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p.relative_to(ROOT)))
    rows=read(ROOT/'formal-results.json')
    assert len(rows)==6
    assert len(list(ROOT.glob('q*/formal/logs/*.jlog')))==6
    for r in rows:
        base=ROOT/f"q{r['problem']}/formal"
        assert digest(base/r['official_log'])==r['official_log_sha256']
        actions=[json.loads(x) for x in (base/r['actions']).read_text(encoding='utf-8').splitlines()]
        requests={e['payload']['request_id']:e for e in actions if e['kind']=='request'}
        accepted=[e for e in actions if e['kind']=='response' and e.get('response',{}).get('accepted')]
        enters=[e['response'] for e in accepted if requests[e['request_id']]['path']=='/enter']
        exits=[e['response'] for e in accepted if requests[e['request_id']]['path']=='/exit']
        assert len(enters)==len(exits)==1
        cleared={requests[e['request_id']]['payload']['channel'] for e in accepted
                 if requests[e['request_id']]['path']=='/clear' and e['response'].get('clear_result')=='success'}
        assert len(cleared)==r['cleared_count']
        assert abs(exits[0]['virtual_time_s']-r['virtual_time_s'])<1e-6
        assert abs((exits[0]['real_timestamp_ms']-enters[0]['real_timestamp_ms'])/1000-r['program_runtime_s'])<1e-9
        assert abs(r['virtual_time_s']/r['cleared_count']-r['average_clear_time_s'])<1e-9
        assert all(e['payload'].get('robot_id')=='ANONYMIZED' for e in requests.values())
        assert all(e['request_id'] in requests for e in actions if e['kind']=='response')
    a=read(ROOT/'q3/analysis/data/analysis.json')
    assert a['official']['literature']['runs']==30
    assert a['official']['v4']['runs']==a['official']['v6']['runs']==50
    assert a['local']['paired_successes']==30
    b=read(ROOT/'q4/analysis/evidence/official_rows.json')
    assert len(b)==90
    for name in ('cautious','m07','m32'):assert sum(x['strategy']==name for x in b)==30
    for p in ROOT.rglob('config.json'):raise AssertionError(f'Private config must not be published: {p.name}')
    print('PASS: file hashes, complete Python syntax, 6 original official logs, official timestamps/time ratios, anonymous request-response links, and practice sample counts.')

if __name__=='__main__':main()
