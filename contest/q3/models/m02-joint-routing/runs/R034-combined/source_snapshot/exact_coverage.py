"""Sufficient circle-arrangement certificate; coarse samples only guide routing."""
import math
import numpy as np
from legacy_strategy import Coverage


def arrangement_certificate(points, radius=999.99, arena_radius=1800.):
    pts=np.unique(np.asarray(points,float).reshape(-1,2),axis=0)
    if not len(pts):return False,np.array([arena_radius,0.])
    angles=[0.]
    for p in pts:
        d=float(np.linalg.norm(p))
        if d+arena_radius<=radius:return True,None
        if d<1e-10:continue
        cosine=(d*d+arena_radius**2-radius**2)/(2*d*arena_radius)
        if -1<=cosine<=1:
            a=math.atan2(p[1],p[0]);delta=math.acos(cosine)
            angles += [(a-delta)%(2*math.pi),(a+delta)%(2*math.pi)]
    angles=sorted(set(angles))
    for i,a in enumerate(angles):
        b=angles[i+1] if i+1<len(angles) else angles[0]+2*math.pi
        q=arena_radius*np.array([math.cos((a+b)/2),math.sin((a+b)/2)])
        if np.min(np.linalg.norm(pts-q,axis=1))>radius+1e-7:return False,q
    # Any bounded uncovered interior component must have a vertex made by
    # circle boundaries. Requiring a third disk's strict interior at all such
    # crossings excludes it. Degenerate coincidences may be rejected safely.
    for i in range(len(pts)):
        for j in range(i):
            v=pts[i]-pts[j];d=float(np.linalg.norm(v))
            if d<1e-10 or d>2*radius:continue
            mid=(pts[i]+pts[j])/2
            normal=np.array([-v[1],v[0]])/d
            half=math.sqrt(max(0.,radius**2-d*d/4))
            for q in [mid+half*normal,mid-half*normal]:
                if np.linalg.norm(q)>=arena_radius-1e-7:continue
                distances=np.linalg.norm(pts-q,axis=1)
                distances[[i,j]]=float('inf')
                if np.min(distances)>=radius-1e-7:return False,q
    return True,None


class ExactCoverage(Coverage):
    def __init__(self):
        super().__init__(level=6)
        self.centers=self.centers[np.linalg.norm(self.centers,axis=1)<=1800]
        self.covered=np.zeros((21,len(self.centers)),dtype=bool)
        self.cache={}

    def mask(self,point):
        return np.sum((self.centers-np.asarray(point))**2,axis=1)<=999.99**2

    def status(self,channel):
        key=tuple(tuple(p) for p in self.samples[channel])
        if key not in self.cache:self.cache[key]=arrangement_certificate(key)
        return self.cache[key]

    def absent(self,channel):return self.status(channel)[0]
