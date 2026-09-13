"""Continuous position/heading certificate; no simulator or truth access."""
import math
import numpy as np
from scipy.spatial import ConvexHull, QhullError
from optimize import RING

class Coverage:
    def __init__(self):
        self.points=np.array(RING['points'],dtype=float)
        self.corners=np.array([[r['lo'],[r['hi'][0],r['lo'][1]],r['hi'],[r['lo'][0],r['hi'][1]]] for r in RING['proof']])
        self.witness=[list(r['stations']) for r in RING['proof']]
        self.active=set(range(len(self.points)))
        self.distances=np.linalg.norm(self.corners[:,None,:,:]-self.points[None,:,None,:],axis=3).max(axis=2)

    def proposal(self,remove,q=None):
        """Certify every affected square using any remaining nearby viewpoints."""
        if q is None:
            points=self.points;distances=self.distances;active=sorted(self.active-{remove})
        else:
            points=np.vstack([self.points,q]);extra=np.linalg.norm(self.corners-q,axis=2).max(axis=1)
            distances=np.column_stack([self.distances,extra]);active=sorted(self.active-{remove})+[len(self.points)]
        updates={}
        for ci,old in enumerate(self.witness):
            if remove not in old:continue
            ids=[i for i in active if distances[ci,i]<=999.99]
            if len(ids)<3:return None
            try:h=ConvexHull(points[ids])
            except QhullError:return None
            if np.max(self.corners[ci]@h.equations[:,:2].T+h.equations[:,2])>1e-8:return None
            updates[ci]=[ids[i] for i in h.vertices]
        return updates

    def commit(self,remove,q,updates):
        self.active.remove(remove)
        if q is not None:
            self.active.add(len(self.points));self.points=np.vstack([self.points,q])
            extra=np.linalg.norm(self.corners-q,axis=2).max(axis=1)
            self.distances=np.column_stack([self.distances,extra])
        for ci,ids in updates.items():self.witness[ci]=ids

    def with_points(self,qs):
        clone=Coverage.__new__(Coverage)
        clone.corners=self.corners;clone.witness=self.witness.copy()
        clone.points=np.vstack([self.points,qs])
        clone.active=self.active|set(range(len(self.points),len(clone.points)))
        extra=np.linalg.norm(self.corners[:,None,:,:]-np.asarray(qs)[None,:,None,:],axis=3).max(axis=2)
        clone.distances=np.column_stack([self.distances,extra])
        return clone

    def certificate(self):
        return dict(points=self.points.tolist(),active=sorted(self.active),witness=self.witness)
