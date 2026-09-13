"""Cost-aware localization and paid sharing of intermediate sensing sites.

Inspired by the cost objectives of Vander Hook (2014), multi-target planning
of Engin & Isler (2020), and approach-to-source routing in Gu et al. (2018).
No Gaussian guarantees, true target inputs, or free simultaneous sensing.
"""
import copy
import math
import numpy as np
from convex_cover import ConvexCoverPlanner
from legacy_strategy import Track,CLEAR_RADIUS,EPS
from bearing_geometry import diameter
from clearance_geometry import nearest_clear_point
from reception_region import reception_violation


class RefinedTrack(Track):
    def safe_clear_point(self,position):
        if self.radius>CLEAR_RADIUS:return None
        return nearest_clear_point(self.poly,position,CLEAR_RADIUS,self.center)


def reception_safe(track,q):
    if np.max(np.linalg.norm(track.poly-q,axis=1))<=999.9:return True
    first=track.history[0]
    if first['measure_result']!='direction':return False
    angle=math.radians(first['svd_deg']);u=np.array([math.cos(angle),math.sin(angle)])
    v=np.array([-u[1],u[0]]);d=q-np.asarray(first['position'])
    a,b=np.dot(d,u),np.dot(d,v);l2=np.dot(d,d);ep=math.radians(EPS)
    return l2<=1000**2-1e-3 and l2<=2000*(a*math.cos(ep)-abs(b)*math.sin(ep))-1e-3


def forecast(track,start,first_point,truth,error,exit_point=None):
    t=copy.copy(track);t.poly=track.poly.copy();t.history=list(track.history)
    p=np.asarray(start);q=first_point;cost=0.
    for k in range(5):
        cost+=float(np.linalg.norm(q-p))/5+5;p=q
        if np.linalg.norm(truth-q)<=5:obs={'measure_result':'near'}
        else:
            angle=math.degrees(math.atan2(truth[1]-q[1],truth[0]-q[0]))
            obs={'measure_result':'direction','svd_deg':round((angle+error)%360,2)%360}
        t.update(q,obs)
        clear=t.safe_clear_point(q)
        if clear is not None:
            cost+=float(np.linalg.norm(clear-q))/5+5
            if exit_point is not None:cost+=float(np.linalg.norm(clear-exit_point))/5
            return cost
        q=t.next_point(p)
    return cost+1000.


class CostAwarePlanner(ConvexCoverPlanner):
    def __init__(self,robot,*,projection=True,cost_action=False,cost_risk=.25,
                 intermediate_known=False,intermediate_gain=2.,exit_cost=False,exact_reception=False,**kwargs):
        super().__init__(robot,**kwargs)
        self.projection=projection;self.cost_action=cost_action;self.cost_risk=cost_risk
        self.intermediate_known=intermediate_known;self.intermediate_gain=intermediate_gain
        self.exit_cost=exit_cost
        self.exact_reception=exact_reception

    def observe(self,point,channel):
        result=super().observe(point,channel)
        if self.projection and channel in self.tracks and not isinstance(self.tracks[channel],RefinedTrack):
            track=RefinedTrack(channel);track.__dict__=self.tracks[channel].__dict__
            self.tracks[channel]=track
        return result

    def pick_point(self,track):
        start=np.asarray(self.robot.position);center=track.center
        default=track.next_point(start)
        _,(i,j)=diameter(track.poly);a,b=track.poly[i],track.poly[j]
        direction=b-a;normal=np.array([-direction[1],direction[0]])/max(np.linalg.norm(direction),1e-9)
        candidates=[default,start,center]
        for f in [.35,.7,1.]:
            mid=start+f*(center-start)
            for offset in [-60.,0.,60.]:candidates.append(mid+offset*normal)
        unique=[]
        for q in candidates:
            if any(math.dist(q,h['position'])<.1 for h in track.history):continue
            if any(np.linalg.norm(q-p)<.1 for p in unique):continue
            safe=reception_safe(track,q)
            if not safe and self.exact_reception:
                safe=reception_violation(track.poly,track.history[0]['position'],q)[0]<=-.01
            if safe:unique.append(np.asarray(q))
        samples=[a*.9+center*.1,b*.9+center*.1,center]
        others=[t.center for c,t in self.tracks.items() if c!=track.channel and c not in self.robot.cleared]
        exit_point=min(others,key=lambda p:np.linalg.norm(p-center)) if self.exit_cost and others else None
        scores=[]
        for q in unique:
            values=[forecast(track,start,q,x,e,exit_point) for x in samples for e in [-1.,0.,1.]]
            score=(1-self.cost_risk)*np.mean(values)+self.cost_risk*np.max(values)
            scores.append(float(score))
        if not scores:return default
        best=int(np.argmin(scores))
        self.robot.record(dict(kind='cost_action',channel=track.channel,
            candidates=[dict(point=q.tolist(),score_s=s) for q,s in zip(unique,scores)],selected=best,
            scoring='representative geometric scenarios; not a continuous minimax certificate'))
        return unique[best]

    def solve_track(self,track):
        # The first observation may replace Track by RefinedTrack; always refresh.
        channel=track.channel
        if not (self.cost_action or self.intermediate_known or self.intermediate_gain<1.):
            return super().solve_track(track)
        for _ in range(16):
            self.robot.check_budget();track=self.tracks[channel]
            if track.radius<=CLEAR_RADIUS:return super().solve_track(track)
            q=self.pick_point(track) if self.cost_action else track.next_point(np.asarray(self.robot.position))
            if self.observe(q,channel)['measure_result']=='no_signal':
                raise ArithmeticError('Certified reception point lost signal')
            if self.intermediate_known or self.intermediate_gain<1.:
                old_gain,old_info=self.scan_gain,self.info_maxobs
                self.scan_gain=self.intermediate_gain
                if not self.intermediate_known:self.info_maxobs=0
                try:self.at_site_scan(self.robot.position)
                finally:self.scan_gain,self.info_maxobs=old_gain,old_info
        raise RuntimeError('Cost-aware localization iteration limit')
