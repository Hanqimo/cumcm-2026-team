"""Conservative cell rejection for joint position/radius/heading feasibility.
Closed relaxed arcs retain zero-measure and boundary possibilities.
"""
import math
import numpy as np
from shapely.geometry import box
from shapely.affinity import affine_transform
from shapely.ops import unary_union
TAU=2*math.pi

def arc_intersection(arcs,angle,width):
    if width>=math.pi:return arcs
    lo=(angle-width)%TAU;hi=lo+2*width
    pieces=[(lo,min(hi,TAU))]
    if hi>=TAU:pieces.append((0.,hi-TAU))
    return [(max(a,c),min(b,d)) for a,b in arcs for c,d in pieces if max(a,c)<=min(b,d)]

def reject(center,rho,history):
    positive=[h for h in history if h['measure_result']!='no_signal']
    negative=[h for h in history if h['measure_result']=='no_signal']
    pd=[(np.asarray(h['point'])-center) for h in positive]
    lower=max([1000.]+[float(np.linalg.norm(d))-rho for d in pd])
    if lower>1500.+1e-5:return dict(reason='radius impossible',lower_radius=lower)
    forced=[j for j,h in enumerate(negative) if np.linalg.norm(np.asarray(h['point'])-center)+rho<lower-1e-5]
    if not forced:return None # Omnidirectional compatibility not ruled out.
    arcs=[(0.,TAU)]
    for d in pd+[center-np.asarray(negative[j]['point']) for j in forced]:
        distance=float(np.linalg.norm(d))
        if distance<=rho+1e-8:continue
        width=math.pi/2+math.asin(min(1.,rho/distance))+1e-9
        arcs=arc_intersection(arcs,math.atan2(d[1],d[0]),width)
        if not arcs:return dict(reason='joint heading impossible',lower_radius=lower,forced_negative_indices=forced)
    return None

def tighten(region,history,resolution=10.,max_boxes=4096):
    if not any(h['measure_result']=='no_signal' for h in history):return region,dict(boxes=0,rejected=[])
    rectangle=np.array(region.minimum_rotated_rectangle.exterior.coords[:-1]);u=rectangle[1]-rectangle[0];u/=max(np.linalg.norm(u),1e-12);v=np.array([-u[1],u[0]])
    transformed=affine_transform(region,[u[0],u[1],v[0],v[1],0,0]);queue=[transformed.bounds];removed=[];certificates=[];count=0
    while queue and count<max_boxes:
        bounds=queue.pop();g=transformed.intersection(box(*bounds))
        if g.is_empty or g.area<=1e-12:continue
        a,b,c,d=g.bounds;center=(np.array([(a+c)/2,(b+d)/2])@np.array([u,v]));rho=math.hypot(c-a,d-b)/2+2e-6;count+=1
        proof=reject(center,rho,history)
        if proof is not None:
            # The padded rectangle is INSIDE the certified disk. Its overlap
            # avoids coincident polygon boundary fragments from separate clips.
            world=affine_transform(box(a-1e-6,b-1e-6,c+1e-6,d+1e-6),[u[0],v[0],u[1],v[1],0,0]);removed.append(world)
            certificates.append(dict(center=center.tolist(),radius=rho,wkt=world.wkt,**proof));continue
        if max(c-a,d-b)<=resolution:continue
        if c-a>=d-b:
            middle=(a+c)/2;queue.extend([(a,b,middle,d),(middle,b,c,d)])
        else:
            middle=(b+d)/2;queue.extend([(a,b,c,middle),(a,middle,c,d)])
    result=region.difference(unary_union(removed)) if removed else region
    if result.is_empty:raise ArithmeticError('joint feasible region unexpectedly empty')
    if not result.is_valid:raise ArithmeticError('joint feasible region invalid topology')
    return result,dict(boxes=count,budget_remaining_boxes=len(queue),rejected=certificates)
