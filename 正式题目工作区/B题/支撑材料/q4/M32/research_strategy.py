"""Ablate posterior-based routing and posterior-centered radio candidates.

MEC geometry is restored before any paid action or safety certificate.
"""
from m07 import Planner as M07
from m13 import Planner as Parent

class Planner(Parent):
    def __init__(self,robot,policy='baseline'):
        if policy not in ['baseline','route','local','both']:raise ValueError(policy)
        super().__init__(robot,'posterior_mean');self.m16=policy

    def joint_order(self,remaining):
        if self.m16 in ['baseline','local']:return M07.joint_order(self,remaining)
        return super().joint_order(remaining)

    def select(self,t):
        if self.m16 not in ['local','both']:return super().select(t)
        representative=self.representative(t);original=t.center.copy()
        try:
            t.center=representative
            q=super().select(t)
        finally:t.center=original
        if q is not None:self.robot.record(dict(kind='posterior_radio_candidate',channel=t.channel,mec_center=original.tolist(),representative=representative.tolist(),point=q.tolist()))
        return q
