"""Exact finite candidates for maximum distance to nearest sensing site in a disk."""
import itertools
import numpy as np
from legacy_strategy import Coverage


def covering_radius(sites,arena_radius=1800.):
    p=np.unique(np.asarray(sites,float).reshape(-1,2),axis=0)
    if not len(p):return float('inf'),np.array([arena_radius,0.])
    candidates=[np.array([arena_radius,0.])]
    norms=np.linalg.norm(p,axis=1)
    candidates.extend(-arena_radius*p[norms>1e-10]/norms[norms>1e-10,None])
    for i,a in enumerate(p):
        for b in p[:i]:
            d=b-a;length=np.linalg.norm(d)
            if length<1e-10:continue
            normal=d/length;offset=np.dot((a+b)/2,normal)
            if abs(offset)>arena_radius:continue
            foot=offset*normal;side=np.sqrt(max(0.,arena_radius**2-offset**2))*np.array([-normal[1],normal[0]])
            candidates.extend([foot+side,foot-side])
    triples=np.array(list(itertools.combinations(range(len(p)),3)),dtype=int)
    if len(triples):
        a,b,c=p[triples[:,0]],p[triples[:,1]],p[triples[:,2]]
        u=b-a;v=c-a;det=u[:,0]*v[:,1]-u[:,1]*v[:,0]
        ok=abs(det)>1e-12*np.maximum(1.,np.linalg.norm(u,axis=1)*np.linalg.norm(v,axis=1))
        a,u,v,det=a[ok],u[ok],v[ok],det[ok]
        hu=np.sum(u*u,axis=1)/2;hv=np.sum(v*v,axis=1)/2
        centers=a+np.column_stack([(hu*v[:,1]-hv*u[:,1])/det,(u[:,0]*hv-v[:,0]*hu)/det])
        candidates.extend(centers[np.linalg.norm(centers,axis=1)<=arena_radius])
    x=np.asarray(candidates);values=np.min(np.linalg.norm(x[:,None,:]-p[None,:,:],axis=2),axis=1)
    k=int(np.argmax(values));return float(values[k]),x[k].copy()


class HybridCoverage(Coverage):
    def __init__(self):
        super().__init__();self.exact_cache={}

    def exact_status(self,sites):
        key=tuple(sorted(set(tuple(float(x) for x in p) for p in sites)))
        if key not in self.exact_cache:self.exact_cache[key]=covering_radius(key)
        return self.exact_cache[key]

    def absent(self,channel):
        return super().absent(channel) or self.exact_status(self.samples[channel])[0]<=999.98
