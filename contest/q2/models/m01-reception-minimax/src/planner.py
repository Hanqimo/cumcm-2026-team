"""Reusable first-version Q2 planner for arbitrary initial position and bearing.

Uses only supplied observable inputs. It searches a finite grid on BOTH sides
of the initial bearing, since the fixed arena is not generally symmetric there.
No simulator I/O is performed; the caller selects the travel budget.
"""
import numpy as np
from second_point import (first_region,unit,in_candidate,to_global,
    candidate_margins,worst_radius_upper)


def plan_next_observation(sensor,theta,budget,epsilon_deg=1.,lateral_min=20.,
                          disk_sides=360,final_bin_width_deg=.05):
    if not 0 < budget <= 1000:
        raise ValueError('This first-version generic planner supports 0 < B <= 1000 m')
    poly=first_region(sensor,theta,epsilon_deg=epsilon_deg,sides=disk_sides)
    candidates=[]
    lengths=np.linspace(budget/5,budget,5)
    for length in lengths:
        for alpha in sorted(set(list(range(10,81,10))+[45])):
            for sign in [-1,1]:
                local=length*unit(sign*alpha)
                if not in_candidate(local,epsilon_deg=epsilon_deg,budget=budget,lateral_min=lateral_min):continue
                q=to_global(local,sensor,theta)
                coarse=worst_radius_upper(poly,q,epsilon_deg=epsilon_deg,bin_width_deg=.5)
                candidates.append((coarse['radius_upper_m'],local,q))
    if not candidates:
        return {'status':'empty_candidate_grid','point':None,
          'reason':'No grid point satisfies the travel, reception and lateral constraints; this does not prove the continuous set empty'}
    shortlist=sorted(candidates,key=lambda r:r[0])[:6]
    best=None
    for _,local,q in shortlist:
        result=worst_radius_upper(poly,q,epsilon_deg=epsilon_deg,bin_width_deg=final_bin_width_deg)
        if best is None or result['radius_upper_m']<best['radius_upper_m']:
            best={'status':'recommended_finite_grid','point':q.tolist(),'local_displacement':local.tolist(),
              'radius_upper_m':result['radius_upper_m'],'travel_m':float(np.linalg.norm(local)),
              'movement_and_measure_s':float(np.linalg.norm(local)/5+5),
              'constraint_margins_m':candidate_margins(local,epsilon_deg=epsilon_deg,budget=budget,lateral_min=lateral_min),
              'prediction':result,'number_of_coarse_candidates':len(candidates),
              'limitations':['omnidirectional source only','not continuous global optimal','not total clearance-time optimal']}
    return best
