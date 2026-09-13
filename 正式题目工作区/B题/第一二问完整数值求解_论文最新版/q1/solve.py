"""第一问完整流程：半平面交、区域直径、最小包围圆和最近保证清除位置。"""
import math
import numpy as np
from .bearing_geometry import observations_halfplanes,halfplane_region,summarize_region
from .clearance_geometry import nearest_clear_point


def solve(data):
    observations=data.get('observations')
    if not isinstance(observations,list) or not observations:raise ValueError('observations 必须是非空观测列表。')
    for observation in observations:
        p=np.asarray(observation.get('position'),float)
        if p.shape!=(2,) or not np.all(np.isfinite(p)):raise ValueError('每个 position 必须是两个有限坐标。')
        if not math.isfinite(float(observation.get('bearing_deg',float('nan')))):raise ValueError('每次观测需要有限的 bearing_deg。')
    epsilon=float(data.get('epsilon_deg',1))
    A,b=observations_halfplanes(observations,epsilon)
    region=halfplane_region(A,b)
    result=summarize_region(region)
    result.update(observations=observations,epsilon_deg=epsilon,units={'length':'m','angle':'degree'},physical_clear_radius_m=20,
                  halfplanes={'A':A.tolist(),'b':b.tolist()},
                  model='directed_bearing_halfplanes_and_minimum_enclosing_circle')
    result['clearance']=None
    if region.status in ('empty','unbounded'):
        result['message']='观测条件不相容。' if region.status=='empty' else '角域交集无界，无法仅由这些测向约束给出有限包围圆。'
        return result
    result['physical_threshold_near_boundary']=abs(result['cover_radius_m']-20)<=1e-7
    # Numerical tolerance is reported, not subtracted from the physical threshold.
    if 'current_position' in data:
        p=np.asarray(data['current_position'],float)
        if p.shape!=(2,) or not np.all(np.isfinite(p)):raise ValueError('current_position 必须是两个有限坐标。')
        radius=float(data.get('engineering_radius_m',19.5))
        if not 0<radius<=20:raise ValueError('engineering_radius_m 必须在 (0,20] 内。')
        c=np.array(result['cover_center'])
        q=nearest_clear_point(region.vertices,p,radius,feasible_point=c)
        result['clearance']={'engineering_radius_m':radius,'feasibility_tolerance_m':1e-8,'current_position':p.tolist(),
                             'engineering_feasible':q is not None,'position':None if q is None else q.tolist(),
                             'move_distance_m':None if q is None else float(np.linalg.norm(q-p)),
                             'max_source_distance_m':None if q is None else float(np.max(np.linalg.norm(region.vertices-q,axis=1)))}
    return result
