"""M07: action substitution, guaranteed-visible recovery, route portfolios."""
import math
import numpy as np
from shapely.geometry import Point
from m06 import Planner as Parent

class Planner(Parent):
    def __init__(self,robot,policy='baseline'):
        if policy not in ['baseline','probe65','probe85','hull','portfolio','sticky','fusion','probe_hull','sticky_probe']:raise ValueError(policy)
        super().__init__(robot,'count');self.m07=policy
        self.threshold=.85 if policy=='probe85' else .65
        self.probe=policy in ['probe65','probe85','fusion','probe_hull','sticky_probe']
        self.recover=policy in ['hull','fusion','probe_hull']
        self.multi=policy in ['portfolio','sticky','fusion','sticky_probe']
        self.previous_order=[];self.recovery_count={};self.recovery_candidates=None

    def candidates(self,t):
        return self.recovery_candidates if self.recovery_candidates is not None else super().candidates(t)

    def select(self,t):
        if not self.recover or t.history[-1]['measure_result']!='no_signal' or self.recovery_count.get(t.channel,0)>=2:return super().select(t)
        pts=np.array([h['point'] for h in t.positive])
        if len(pts)<2:return super().select(t)
        dm=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2);i,j=np.unravel_index(np.argmax(dm),dm.shape)
        raw=[pts.mean(axis=0)]+[(1-f)*pts[i]+f*pts[j] for f in [.25,.5,.75]]+[(pts[-1]+pts[-2])/2]
        qs=[]
        for q in raw:
            if all(math.dist(q,h['point'])>2 for h in t.history) and all(math.dist(q,x)>1e-6 for x in qs):qs.append(q)
        if not qs:return super().select(t)
        self.recovery_candidates=qs
        try:q=super().select(t)
        finally:self.recovery_candidates=None
        self.recovery_count[t.channel]=self.recovery_count.get(t.channel,0)+1
        self.robot.record(dict(kind='visible_hull_recovery',channel=t.channel,positive_points=pts.tolist(),point=q.tolist()))
        return q

    def solve(self,ch):
        if not self.probe:return super().solve(ch)
        t=self.tracks[ch];probed=False
        for _ in range(10):
            if t.radius<=19.5:
                if not self.try_clear(t,t.center,'enclosing circle certificate'):raise ArithmeticError('certified clear failed')
                return
            q=self.select(t)
            if q is None:break
            if not probed:
                fraction=t.region.intersection(Point(*q).buffer(19.999,quad_segs=24)).area/max(t.region.area,1e-12)
                if fraction>=self.threshold:
                    probed=True
                    self.robot.record(dict(kind='pre_radio_probe',channel=ch,point=q.tolist(),fraction=float(fraction),region=t.region.wkt,threshold=self.threshold))
                    if self.try_clear(t,q,'one optical attempt at planned radio viewpoint'):return
            # After failed probe, keep the originally selected paid radio viewpoint.
            z=self.observe(q,ch)
            if z['measure_result']=='no_signal':self.lost+=1
        self.optical_cover(t)

    def joint_order(self,remaining):
        baseline=super().joint_order(remaining)
        if not self.multi or len(baseline)<2:return baseline
        keys=[('site',i) for i in sorted(remaining)]+[('target',ch) for ch in sorted(self.tracks) if ch not in self.robot.cleared]
        pts=np.vstack([self.robot.position]+[self.sites[k] if kind=='site' else self.tracks[k].center for kind,k in keys])
        dm=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2);index={key:i+1 for i,key in enumerate(keys)}
        def cost(order):return float(sum(dm[a,b] for a,b in zip(order[:-1],order[1:])))
        def insert(order):
            todo=set(range(1,len(pts)))-set(order)
            while todo:
                best=None
                for k in sorted(todo):
                    for pos in range(1,len(order)+1):
                        a=order[pos-1];delta=dm[a,k]
                        if pos<len(order):b=order[pos];delta+=dm[k,b]-dm[a,b]
                        choice=(delta,k,pos)
                        if best is None or choice<best:best=choice
                _,k,pos=best;order.insert(pos,k);todo.remove(k)
            return order
        def improve(order):
            for _ in range(100):
                best=-1e-7;change=None
                for i in range(1,len(order)-1):
                    a,b=order[i-1],order[i]
                    for j in range(i+1,len(order)):
                        c=order[j];delta=dm[a,c]-dm[a,b]
                        if j+1<len(order):d=order[j+1];delta+=dm[b,d]-dm[c,d]
                        if delta<best:best=delta;change=(i,j)
                if change is None:break
                i,j=change;order[i:j+1]=order[i:j+1][::-1]
            return order
        orders=[[0]+[index[k] for k in baseline]]
        warm=[0]+[index[k] for k in self.previous_order if k in index]
        orders.append(improve(insert(warm)))
        far=int(np.argmax(dm[0,1:]))+1;orders.append(improve(insert([0,far])))
        costs=[cost(o) for o in orders];chosen=int(np.argmin(costs))
        if self.m07 in ['sticky','sticky_probe'] and costs[1]<=min(costs)+25:chosen=1
        answer=[keys[i-1] for i in orders[chosen][1:]];self.previous_order=answer.copy()
        self.robot.record(dict(kind='routing_portfolio',lengths_m=costs,chosen=chosen,order=[dict(kind=k,id=i) for k,i in answer]))
        return answer
