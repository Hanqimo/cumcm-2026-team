"""Read-only audit of saved official practice responses and local assumptions.

No simulator calls, new tests, decryption, or hidden-case reconstruction.
Output excludes robot/team identifiers and preserves source hashes.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SIM=ROOT.parent/'B-simulator'
LOGS=SIM/'Jammers-simulator-full-win64/Jammers-simulator-full/JammersSimulatorData/behavior-logs'


def utc_millis(s):
    fmt='%Y-%m-%dT%H:%M:%S.%fZ' if '.' in s else '%Y-%m-%dT%H:%M:%SZ'
    return dt.datetime.strptime(s,fmt).replace(tzinfo=dt.timezone.utc).timestamp()*1000


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    assert not (OUT/'summary.json').exists(),'Do not overwrite a completed audit'
    sources={};official=[];rows=[];ledgers=[]
    def source(p):
        sources[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(LOGS.glob('*.result.json')):
        d=json.loads(p.read_text(encoding='utf-8-sig'));source(p)
        packaged=p.with_name(p.name.replace('.result.json','.jlog'))
        # Hash an opaque file only; never decode it.
        d['opaque_jlog_hash_matches']=packaged.is_file() and hashlib.sha256(packaged.read_bytes()).hexdigest()==d['package_sha256']
        official.append(d)
    for summary in sorted(SIM.glob('*/runs/*/summary.json')):
        folder=summary.parent;actions=folder/'actions.jsonl'
        if not actions.is_file():continue
        s=json.loads(summary.read_text(encoding='utf-8-sig'));source(summary);source(actions)
        req={};done=set();p=(0.,0.);channel=1;clock=0.;last_clock=0.
        measures=switches=failures=0;cleared={};enter_ms=exit_ms=None
        max_step=max_total=0.;accepted=0;readings=[];same_position={};repeat_conflicts=0
        for line in actions.read_text(encoding='utf-8-sig').splitlines():
            event=json.loads(line)
            if event['kind']=='request':
                req[event['payload']['request_id']]=event
                continue
            if event['kind']!='response':continue
            response=event['response'];rid=event['request_id']
            if event.get('http_status')!=200 or response.get('accepted') is not True or rid in done:continue
            done.add(rid);request=req[rid];path=request['path'];payload=request['payload'];cost=0.
            if path=='/enter':enter_ms=response['real_timestamp_ms']
            if path=='/exit':exit_ms=response['real_timestamp_ms']
            if path in ['/measure','/clear']:
                q=(payload['position']['x'],payload['position']['y']);c=payload['channel']
                move=math.dist(p,q);cost=move/5;p=q
                if path=='/measure':
                    switched=int(c!=channel);switches+=switched;cost+=5+switched;channel=c;measures+=1
                    if c not in cleared:
                        key=(c,q);value=(response['measure_result'],response.get('svd_deg'))
                        if key in same_position and same_position[key]!=value:repeat_conflicts+=1
                        same_position[key]=value
                    readings.append(response['measure_result'])
                else:
                    ok=response['clear_result']=='success';cost+=5 if ok else 3
                    if ok:cleared[c]=q
                    else:failures+=1
                observed=response['virtual_time_s']-last_clock
                discrepancy=abs(cost-observed);max_step=max(max_step,discrepancy)
                ledgers.append(dict(run=folder.name,path=path,position=list(q),channel=c,
                                    reconstructed_delta_s=cost,official_delta_s=observed,error_s=discrepancy))
            clock+=cost;last_clock=response['virtual_time_s'];max_total=max(max_total,abs(clock-last_clock));accepted+=1
        matches=[d for d in official if enter_ms is not None and utc_millis(d['window_started_at_utc'])<=enter_ms<=utc_millis(d['ended_at_utc'])+2
                 and exit_ms is not None and abs(exit_ms-utc_millis(d['ended_at_utc']))<2000]
        assert len(matches)==1,(folder,matches)
        actual=matches[0]
        assert max_step<2e-6 and max_total<.001,(folder,max_step,max_total)
        assert abs(clock-s['virtual_time_s'])<.001
        assert len(cleared)==s['cleared_count'] and len(cleared)==actual['jammer_count']
        radial=np.array([math.hypot(*q) for q in cleared.values()])
        row=dict(run=folder.name,source_folder=str(folder),strategy=s.get('strategy'),policy=s.get('policy'),
                 case_code=actual['case_code'],problem=actual['problem_no'],actual_n=actual['jammer_count'],
                 directional_n=actual['directional_jammer_count'],omni_n=actual['omnidirectional_jammer_count'],
                 clear_count=len(cleared),full=True,time_s=s['virtual_time_s'],per_source_s=s['virtual_time_s']/len(cleared),
                 action_count=accepted,measures=measures,switches=switches,failed_clears=failures,
                 max_step_error_s=max_step,max_cumulative_error_s=max_total,repeat_reading_conflicts=repeat_conflicts,
                 response_wall_s=(exit_ms-enter_ms)/1000,
                 clear_position_mean_radius_m=float(radial.mean()),
                 possible_source_mean_radius_interval_m=[float(np.maximum(0,radial-20).mean()),float(np.minimum(1800,radial+20).mean())],
                 opaque_jlog_hash_matches=actual['opaque_jlog_hash_matches'])
        rows.append(row)
    q4=[r for r in rows if r['problem']==4]
    assert len(q4)==1
    n=q4[0]['actual_n'];k=q4[0]['directional_n']
    # The LOCAL generator fixes one directional and one omni; the remaining
    # N-2 types are Bernoulli(0.5). This is not the official generation law.
    probability=math.comb(n-2,k-1)*.5**(n-2)
    local_paths=[ROOT/'contest/q3/models/m01-region-routing/verification/verify.py',
                 ROOT/'contest/q3/models/m04-service-routing/verification/benchmark.py',
                 ROOT/'contest/q4/models/m01-directional-mesh/verification/benchmark.py',
                 ROOT/'contest/global/problem/B-v1/B题.pdf',
                 ROOT/'contest/global/problem/B-v1/附件/附件1.docx',ROOT/'contest/global/problem/B-v1/附件/附件2.docx']
    for p in local_paths:source(p)
    stratified={}
    for problem,policy,path,key,pname in [
        (3,'service_v5',ROOT/'contest/q3/models/m04-service-routing/runs/R018-frozen-audit/results.json','n','variant'),
        (4,'directional_v1',ROOT/'contest/q4/models/m01-directional-mesh/runs/R006-final-v11/results.json','actual_count','policy')]:
        source(path);local=json.loads(path.read_text(encoding='utf-8'))
        for r in [r for r in rows if r['policy']==policy]:
            group=[a for a in local if a[key]==r['actual_n'] and a[pname]==('v5' if problem==3 else policy)]
            vals=[a['per_source_s' if problem==3 else 'average_s'] for a in group]
            stratified[r['case_code']]=dict(local_cases_same_N=len(vals),local_same_N_mean_s=float(np.mean(vals)),
                                          local_same_N_min_s=min(vals),local_same_N_max_s=max(vals),official_single_case_s=r['per_source_s'],
                                          warning='Different cases and unknown official distribution; descriptive only, not a paired validation')
    result=dict(official_practice_runs=len(rows),official_formal_runs_found=sum(not d.get('practice_run_no') for d in official),
                accepted_actions=sum(r['action_count'] for r in rows),
                movement_measure_clear_actions=len(ledgers),max_action_time_error_s=max(r['max_step_error_s'] for r in rows),
                max_cumulative_error_s=max(r['max_cumulative_error_s'] for r in rows),runs=rows,
                q4_type_count=dict(N=n,K=k,probability_under_local_generator=probability,
                                   assumption='Conditional on N; K=1+Binomial(N-2,0.5); not a formal test of the unknown official law'),
                stratified_descriptive_comparisons=stratified,source_sha256=sources,
                no_new_official_calls=True,opaque_logs_not_decoded=True)
    (OUT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'time-ledger.json').write_text(json.dumps(ledgers,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','runs']},ensure_ascii=False,indent=2))
    print('Cases:',json.dumps([{k:r[k] for k in ['case_code','policy','actual_n','directional_n','per_source_s','possible_source_mean_radius_interval_m']} for r in rows],ensure_ascii=False))


if __name__=='__main__':main()
