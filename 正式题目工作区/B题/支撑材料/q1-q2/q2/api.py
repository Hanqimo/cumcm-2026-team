"""Python API: input/output lengths in m, angles in degrees unless stated otherwise."""
from pathlib import Path
import csv,json,math,subprocess
from build import build


def binary():
    return build()


def validate_scenario(a,beta):
    if not math.isfinite(a) or a<0 or not math.isfinite(beta):
        raise ValueError('a 必须为有限非负数，beta 必须为有限角度。')


def native(a,beta,*args):
    validate_scenario(a,beta)
    run=subprocess.run([str(binary()),str(a),str(beta%360),*map(str,args)],text=True,capture_output=True)
    if run.returncode:raise ValueError(run.stderr.strip() or '数值内核运行失败')
    return run.stdout


def to_global(q,a,beta):
    b=math.radians(beta);x,y=q
    return [a+math.cos(b)*x-math.sin(b)*y,math.sin(b)*x+math.cos(b)*y]


def to_internal(q,a,beta):
    b=math.radians(beta);x,y=q[0]-a,q[1]
    return [math.cos(b)*x+math.sin(b)*y,-math.sin(b)*x+math.cos(b)*y]


def initial_geometry(a,beta):
    result=json.loads(native(a,beta,'info'))
    result['center_global']=to_global(result['center'],a,beta)
    result['points_global']=[to_global(p,a,beta) for p in result['points']]
    return result


def evaluate(a,beta,q,weight=.5,level=6,scan=128,frame='global'):
    if not math.isfinite(weight) or not 0<=weight<=1:raise ValueError('w 必须在 [0,1] 内。')
    if frame not in ('global','internal'):raise ValueError('frame must be global or internal')
    p=to_internal(q,a,beta) if frame=='global' else q
    result={k:float(v) for k,v in next(csv.DictReader(native(a,beta,'eval',*p,level,scan).splitlines())).items()}
    result['admissible']=result['distance_K1']<=1500+1e-7
    result['w']=weight
    # Save raw probabilities; only floating-point excursions are clipped in F.
    result['F']=(1-weight)*result['J']/20+weight*(1-min(1,max(0,result['P_finish'])))
    return result


def feedback_geometry(a,beta,q,kind,theta_deg=0,frame='global'):
    if frame not in ('global','internal'):raise ValueError('frame must be global or internal')
    p=to_internal(q,a,beta) if frame=='global' else q
    theta=math.radians(theta_deg-beta if frame=='global' else theta_deg)
    kinds={'H':0,'normal':1,'N':2}
    if kind not in kinds:raise ValueError('kind must be H, N or normal')
    result=json.loads(native(a,beta,'geometry',*p,kinds[kind],theta))
    result['center_global']=to_global(result['center'],a,beta) if result['nonempty'] else None
    return result
