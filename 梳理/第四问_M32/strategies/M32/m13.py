"""Change only target representation used in global route ordering."""
import numpy as np
from m07 import Planner as Parent
from posterior import position_cloud,median

class Planner(Parent):
    def __init__(self,robot,policy='baseline'):
        if policy not in ['baseline','centroid','posterior_mean','posterior_median']:raise ValueError(policy)
        super().__init__(robot,'portfolio');self.m13=policy;self.representatives={}

    def representative(self,t):
        signature=(len(t.history),t.region.wkb)
        old=self.representatives.get(t.channel)
        if old is not None and old[0]==signature:return old[1]
        if self.m13=='centroid':p=np.array(t.region.centroid.coords[0]);count=0
        else:
            pts,w=position_cloud(t);p=w@pts if self.m13=='posterior_mean' else median(pts,w);count=len(pts)
        self.representatives[t.channel]=(signature,p)
        self.robot.record(dict(kind='route_representative',channel=t.channel,method=self.m13,mec_center=t.center.tolist(),representative=p.tolist(),mec_radius=t.radius,points=count))
        return p

    def joint_order(self,remaining):
        if self.m13=='baseline':return super().joint_order(remaining)
        saved={ch:t.center.copy() for ch,t in self.tracks.items() if ch not in self.robot.cleared}
        # MEC centers are restored before observing, selecting or clearing.
        try:
            for ch in saved:self.tracks[ch].center=self.representative(self.tracks[ch])
            return super().joint_order(remaining)
        finally:
            for ch,c in saved.items():self.tracks[ch].center=c
