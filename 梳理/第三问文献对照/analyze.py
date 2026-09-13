from pathlib import Path
import csv,json,hashlib,math
import numpy as np
from scipy import stats

HERE=Path(__file__).resolve().parent
BATCH=HERE/'official'
OLD=BATCH/'history-v4-v6.csv'
PAIRED=HERE/'paired'
DATA=HERE/'data';DATA.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(r,local=False):
    if local:
        n=r['n'];full=r['full'];time=r['time_s'];d=r['distance_m'];m=r['measures'];sw=r['switches'];f=r['failures'];cl=r['cleared'];case=str(r['seed'])
    else:
        n=int(r['official_jammer_count']);full=str(r['full_clear']).lower()=='true';time=float(r['virtual_time_s']);d=float(r['distance_m']);m=int(r['measure_count']);sw=int(r['switches']);f=int(r['clear_failures']);cl=int(r['cleared_count']);case=r['case_code']
    cost=np.array([d/5,5*m,sw,5*cl,3*f])/n
    assert abs(cost.sum()-time/n)<1e-4,(case,cost.sum(),time/n)
    return dict(case=case,n=n,full=full,time_s=time,per_source_s=time/n,cost=cost.tolist(),distance_m=d,measures=m,switches=sw,failures=f,cleared=cl)
def summary(rows):
    full=[r for r in rows if r['full']];a=np.array([r['per_source_s'] for r in full]);n=len(a)
    return dict(runs=len(rows),full=n,sources=sum(r['n'] for r in rows),mean=float(a.mean()),sd=float(a.std(ddof=1)),median=float(np.median(a)),min=float(a.min()),max=float(a.max()),cost=np.mean([r['cost'] for r in full],axis=0).tolist(),sem_ci95=(a.mean()+np.array([-1,1])*stats.t.ppf(.975,n-1)*a.std(ddof=1)/math.sqrt(n)).tolist())
def welch(a,b):
    a=np.array(a);b=np.array(b);va=a.var(ddof=1)/len(a);vb=b.var(ddof=1)/len(b);se=math.sqrt(va+vb);df=(va+vb)**2/(va**2/(len(a)-1)+vb**2/(len(b)-1));diff=a.mean()-b.mean()
    return dict(saving=float(diff),ci95=(diff+np.array([-1,1])*stats.t.ppf(.975,df)*se).tolist(),df=float(df))

official=read(BATCH/'results.json');assert len(official)==30,'Official batch not yet complete'
for r in official:
    assert r['export_verified']
    # Original official files are retained locally. This portable script
    # recomputes statistics; it does not repeat the original jlog hash audit.
old=list(csv.DictReader(OLD.open(encoding='utf-8-sig')))
groups={'literature':[norm(r) for r in official],'v4':[norm(r) for r in old if r['group']=='v4'],'v6':[norm(r) for r in old if r['group']=='v6']}
report={'official':{k:summary(v) for k,v in groups.items()}}
for key in ['literature','v4']:
    report[key+'_vs_v6']=welch([r['per_source_s'] for r in groups[key] if r['full']],[r['per_source_s'] for r in groups['v6'] if r['full']])
    report[key+'_vs_v6']['saving_percent']=100*(1-report['official']['v6']['mean']/report['official'][key]['mean'])
    common=sorted(set(r['n'] for r in groups[key])&set(r['n'] for r in groups['v6']))
    layers=[]
    for n in common:
        a=[r['per_source_s'] for r in groups[key] if r['n']==n and r['full']];b=[r['per_source_s'] for r in groups['v6'] if r['n']==n and r['full']]
        if not a or not b:continue
        layers.append(dict(n=n,old_count=len(a),v6_count=len(b),weight=len(a)+len(b),old_mean=float(np.mean(a)),v6_mean=float(np.mean(b))))
    weights=np.array([x['weight'] for x in layers]);weights=weights/weights.sum()
    report[key+'_vs_v6']['standardized']={k:float(np.dot(weights,[x[k] for x in layers])) for k in ['old_mean','v6_mean']}
    report[key+'_vs_v6']['strata']=layers

local={key:[norm(r,True) for r in read(PAIRED/key/'results.json')] for key in ['baseline','v6']}
assert all(len(x)==30 for x in local.values())
assert read(PAIRED/'baseline/fixtures.json')==read(PAIRED/'v6/fixtures.json')
pairs=[]
for a,b in zip(local['baseline'],local['v6']):
    assert a['case']==b['case']
    pairs.append(dict(seed=int(a['case']),n=a['n'],both_full=a['full'] and b['full'],baseline=a,v6=b,saving_s=a['per_source_s']-b['per_source_s']))
valid=[p for p in pairs if p['both_full']];d=np.array([p['saving_s'] for p in valid]);median=float(np.median(d));representative=min(valid,key=lambda p:(abs(p['saving_s']-median),p['seed']))
report['local']={k:summary(v) for k,v in local.items()}
report['local'].update(paired_successes=len(valid),wins=int(sum(d>0)),mean_saving=float(d.mean()),median_saving=median,ci95=(d.mean()+np.array([-1,1])*stats.t.ppf(.975,len(d)-1)*d.std(ddof=1)/math.sqrt(len(d))).tolist(),representative=representative)
save(DATA/'official_groups.json',groups);save(DATA/'paired_results.json',pairs);save(DATA/'analysis.json',report)
save(DATA/'official_literature_results.json',official)
print(json.dumps(report,ensure_ascii=False,indent=2))
