"""Check continuous-cell lower bounds and produce conservative near-optimal grid."""
import csv,json,subprocess,math,random
from pathlib import Path
from verify_compare import ROOT,RUN,VERIFY,csv_call
from search_worst import batch

def main():
    r=random.Random(120926);checks=[]
    boxes=[(0,0,1,1),(969.35,497.73,1,1),(906.62,572.79,2,2),(-750,700,200,100),(1500,0,1,1)]
    for _ in range(45):
        if r.random()<.6:x,y=r.uniform(700,1100),r.uniform(300,750)
        else:x,y=r.uniform(-1500,3000),r.uniform(0,1550)
        h=r.choice([100,25,5,.5,.05,.005]);boxes.append((x,y,h,h*.6))
    for x,y,hx,hy in boxes:
        low=float(subprocess.check_output([str(ROOT/'worst_solver'),'cell',*map(str,[x,y,hx,hy])],text=True))
        for dx,dy in [(0,0),(-hx,-hy),(-hx,hy),(hx,-hy),(hx,hy)]:
            q=[x+dx,y+dy]
            if math.hypot(*q)<1e-10:continue
            cert=csv_call(ROOT/'worst_solver','cert',*q,.02)
            assert cert['angle_bound_complete']==1
            assert low<=cert['worst_upper']+1e-5,(x,y,hx,hy,q,low,cert)
            checks.append({'cell':[x,y,hx,hy],'cell_lower':low,'q':q,'point_upper':cert['worst_upper']})
    (VERIFY/'cell_bound_checks.json').write_text(json.dumps(checks,indent=2))
    lower=json.loads((VERIFY/'global_bound_0001.json').read_text())['global_lower_bound']
    threshold=lower*1.01
    rows=batch('local5',[(x,y) for x in range(600,1151,5) for y in range(250,851,5)],8)
    accepted=[];ambiguous=[];possible=[r for r in rows if r['worst_lower']<=threshold]
    for row in possible:
        c=csv_call(ROOT/'worst_solver','cert',row['x'],row['y'],.002)
        if c['worst_upper']<=threshold:accepted.append(c)
        elif c['worst_lower']<=threshold:
            c=csv_call(ROOT/'worst_solver','cert',row['x'],row['y'],1e-5)
            if c['worst_upper']<=threshold:accepted.append(c)
            elif c['worst_lower']<=threshold:ambiguous.append(c)
    if accepted:
        with (RUN/'candidates_1pct_grid5.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(accepted[0]));w.writeheader();w.writerows(accepted)
    report={'relative_tolerance':.01,'threshold_m':threshold,'threshold_based_on_global_lower_bound':True,
        'evaluated_grid_box':[600,1150,250,850],'step_m':5,'evaluated_grid_points':len(rows),
        'accepted_points_north':len(accepted),'boundary_ambiguous_points':ambiguous,
        'x_range':[min(r['x'] for r in accepted),max(r['x'] for r in accepted)],
        'y_range':[min(r['y'] for r in accepted),max(r['y'] for r in accepted)],
        'note':'A conservative subset of the true 1 percent near-optimal region; bounding rectangle is not the region, and this grid is not a proof of exhaustive region coverage.',
        'cell_property_check_count':len(checks)}
    (RUN/'candidates_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
