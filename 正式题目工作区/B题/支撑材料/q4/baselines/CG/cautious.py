"""Literature-inspired bounded-region adaptation, not a reproduction of the EKF paper.

Vander Hook, Tokekar & Isler (2014), Algorithm 1 / equation (9).
Uniform convex-region moments replace the Gaussian EKF estimate. The same M07
search/route/clearance scaffold prevents a missing search guarantee from making
the comparator artificially incomplete. No direction/radius posterior or joint
negative-observation clipping is used. beta=0.05 is fixed before any evaluation.
"""
import math
import numpy as np
from scipy.stats import norm
from m07 import Planner as Parent

def moments(poly):
    """Exact uniform-area first/second moments of a convex polygon by triangles."""
    poly=np.asarray(poly,float);anchor=poly.mean(axis=0)
    weight=0.;first=np.zeros(2);second=np.zeros((2,2))
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        tri=np.array([anchor,a,b]);area=abs(np.linalg.det(np.stack([a-anchor,b-anchor])))/2
        total=tri.sum(axis=0);first+=area*total/3
        second+=area*(tri.T@tri+np.outer(total,total))/12;weight+=area
    if weight<=1e-12:return anchor,np.zeros((2,2))
    mean=first/weight;cov=second/weight-np.outer(mean,mean)
    return mean,(cov+cov.T)/2

class Planner(Parent):
    def __init__(self,robot,policy='cautious'):
        if policy!='cautious':raise ValueError(policy)
        super().__init__(robot,'portfolio')
        self.beta=.05;self.stop_reason=None

    def select(self,t):
        center,cov=moments(t.poly);values,vectors=np.linalg.eigh(cov)
        major=math.sqrt(max(float(values[-1]),0));v=vectors[:,0]
        sigma_beta=math.pi/(2*norm.ppf(1-self.beta/2))
        sigma_s=math.radians(1)/math.sqrt(3)
        radius=major/math.sqrt(sigma_beta**2-sigma_s**2)
        pair=[center+radius*v,center-radius*v]
        fresh=lambda q:all(math.dist(q,h['point'])>2 for h in t.history)
        options=[q for q in pair if fresh(q)]
        recovery=False
        if not options:
            # A no-signal leaves the bounded region unchanged. Rotate the same
            # cautious radius only after both preferred locations were measured;
            # never average repeated same-position measurements as new noise.
            recovery=True
            for k in range(1,6):
                theta=k*math.pi/6;rot=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
                d=rot@v;options=[q for q in [center+radius*d,center-radius*d] if fresh(q)]
                if options:break
        if not options:return None
        q=min(options,key=lambda q:math.dist(q,self.robot.position))
        self.robot.record(dict(kind='literature_cautious_choice',channel=t.channel,center=center.tolist(),
          covariance=cov.tolist(),radius=radius,beta=self.beta,angular_recovery=recovery,
          candidates=[x.tolist() for x in options],selected=q.tolist()))
        return q

    def run(self):
        try:self.stop_reason=super().run()
        finally:self.robot.scanned_sites=len(self.visited)
        return self.stop_reason

    def certificate(self):
        return dict(problem=4,reason=self.stop_reason,complete=bool(self.stop_reason),
            cleared_channels=sorted(self.robot.cleared),observed_but_uncleared=sorted(set(self.tracks)-self.robot.cleared),
            mesh_points=self.sites.tolist(),visited_sites=sorted(self.visited),
            negative_counts={str(k):len(v) for k,v in self.negatives.items()},
            shared_measures=self.shared_measures,optical_fallbacks=self.fallbacks,
            method='bounded-region adaptation of cautious greedy, fixed beta=.05')
