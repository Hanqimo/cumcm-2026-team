"""M16 with certified projection of joint radius/heading constraints."""
from research_strategy import Planner as M16
from joint_region import tighten

class Planner(M16):
    def __init__(self,robot,policy='joint'):
        if policy not in ['baseline','joint']:raise ValueError(policy)
        super().__init__(robot,'both');self.joint_policy=policy

    def observe(self,q,ch):
        z=super().observe(q,ch)
        if self.joint_policy=='baseline' or ch not in self.tracks:return z
        t=self.tracks[ch]
        if not any(h['measure_result']=='no_signal' for h in t.history):return z
        old=t.region;old_radius=t.radius
        new,proof=tighten(old,t.history)
        if not proof['rejected']:return z
        t.region=new;t.refresh()
        self.robot.record(dict(kind='joint_region_certificate',channel=ch,history=t.history.copy(),old_region=old.wkt,new_region=new.wkt,old_radius=old_radius,new_radius=t.radius,proof=proof))
        self.robot.record(dict(kind='region',channel=ch,wkt=t.region.wkt,radius_m=t.radius))
        return z
