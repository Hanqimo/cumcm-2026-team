"""Euclidean projection onto the intersection of equal-radius clear disks."""
import math
import numpy as np


def nearest_clear_point(vertices,position,radius=19.5,feasible_point=None):
    """Return the global nearest safe point, or None if no candidate is feasible.

    An external projection lies on one circular arc, or a two-circle vertex.
    Smooth-arc candidates are radial projections; vertices are enumerated.
    A supplied feasible point is a numerical fallback, not an optimality claim.
    """
    v=np.asarray(vertices,float);p=np.asarray(position,float)
    if not len(v):return None
    def feasible(q):return np.max(np.linalg.norm(v-q,axis=1))<=radius+1e-8
    if feasible(p):return p.copy()
    candidates=[]
    for center in v:
        d=p-center;length=float(np.linalg.norm(d))
        if length>1e-12:
            q=center+radius*d/length
            if feasible(q):candidates.append(q)
    for i,a in enumerate(v):
        for b in v[:i]:
            d=b-a;length=float(np.linalg.norm(d))
            if length<1e-10 or length>2*radius+1e-9:continue
            offset=math.sqrt(max(0.,radius**2-length**2/4))*np.array([-d[1],d[0]])/length
            for q in [(a+b)/2+offset,(a+b)/2-offset]:
                if feasible(q):candidates.append(q)
    if feasible_point is not None and feasible(np.asarray(feasible_point)):
        candidates.append(np.asarray(feasible_point).copy())
    if not candidates:return None
    return min(candidates,key=lambda q:float(np.linalg.norm(q-p))).copy()
