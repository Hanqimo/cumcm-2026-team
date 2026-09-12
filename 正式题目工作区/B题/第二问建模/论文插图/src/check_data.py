"""Semantic and precision checks for plotted fields, level curves and geometry."""
from pathlib import Path
import csv,json,subprocess,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data'
def main():
    comp=json.loads((ROOT.parent/'worstcase/runs/R001/comparison.json').read_text())
    refs={'expected':comp['results']['expected']['uniform_prior_expectation']['E_radius_loss'],
          'worst':comp['results']['minimax']['strict_worst']['worst_upper']}
    contours=json.loads((D/'contours_1pct.json').read_text());cases=[]
    for kind,segments in contours.items():
        for line in segments:
            a=np.array(line)
            for i in np.unique(np.linspace(0,len(a)-1,min(90,len(a))).astype(int)):
                cases.append((kind,*a[i]))
            for i in np.unique(np.linspace(0,len(a)-2,min(50,len(a)-1)).astype(int)):
                cases.append((kind,*((a[i]+a[i+1])/2)))
    with (D/'contour_check_input.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['x','y']);w.writerows((x,y) for _,x,y in cases)
    subprocess.run([str(ROOT/'build/figure_backend'),'batch',str(D/'contour_check_input.csv'),str(D/'contour_check.csv'),'5'],check=True)
    check=list(csv.DictReader((D/'contour_check.csv').open()));deviations={'expected':[],'worst':[]}
    assert len(check)==len(cases),'Every selected contour point must be evaluated.'
    for (kind,x,y),r in zip(cases,check):
        value=float(r['expected_radius' if kind=='expected' else 'worst_upper'])
        deviations[kind].append(100*(value/refs[kind]-1)-1)
    for kind,tolerance in [('expected',.001),('worst',.005)]:
        assert max(abs(v) for v in deviations[kind])<tolerance,f'{kind} 1% contour failed numerical check.'
    geo=json.loads((D/'geometry.json').read_text());residual={}
    for kind,polygon in geo['polygons'].items():
        cp=geo['control'][kind];p=np.array(polygon);residual[kind]=float((np.linalg.norm(p-np.array(cp['center']),axis=1)-cp['radius']).max())
        assert residual[kind]<1e-6
    curve=list(csv.DictReader((D/'branch_curve.csv').open()))
    errors=[]
    for r in curve:
        peak=max(float(r['normal_lower']),float(r['no_signal_radius']))
        gap=float(r['worst_upper'])-float(r['worst_lower'])
        assert 0<=gap<=2.00001e-5 and peak<=float(r['worst_upper'])+1e-9
        # no_signal_radius is its upper bound, while worst_lower uses its lower
        # bound; the preserved solver adds 2e-7 m to each side of the geometry.
        assert abs(peak-float(r['worst_lower']))<4.1e-7
        errors.append(float(r['worst_upper'])-peak)
    endpoints={}
    for t,name in [(0,'expected'),(1,'minimax')]:
        r=min(curve,key=lambda r:abs(float(r['t'])-t))
        endpoints[name]={'expected_radius_level3_deviation_m':float(r['expected_radius'])-comp['results'][name]['uniform_prior_expectation']['E_radius_loss'],
            'worst_lower_deviation_m':float(r['worst_lower'])-comp['results'][name]['strict_worst']['worst_lower']}
        assert abs(endpoints[name]['expected_radius_level3_deviation_m'])<3e-5
        assert abs(endpoints[name]['worst_lower_deviation_m'])<1e-7
    summary={'contour_checks':len(cases),'contour_deviation_percentage_points':{k:{'min':min(v),'max':max(v),'max_abs':max(abs(a) for a in v)} for k,v in deviations.items()},
        'geometry_max_circle_residual_m':residual,'branch_envelope_max_gap_m':max(errors),'curve_points':len(curve),'reference_point_checks':endpoints}
    (D/'checks.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
