"""Continuous waypoint relocation with an explicit full-coverage constraint."""
import math
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from joint_strategies import JointPlanner,open_route
from bearing_geometry import enclosing_circle,diameter


class FlexibleCoverPlanner(JointPlanner):
    def __init__(self,robot,*,cover_sweeps=2,merge_stations=True,merge_target_scans=False,**kwargs):
        super().__init__(robot,family='adaptive',**kwargs)
        self.cover_sweeps=cover_sweeps
        self.merge_stations=merge_stations
        self.merge_target_scans=merge_target_scans

    def candidates(self):
        targets=[]
        for c,t in self.tracks.items():
            if c in self.robot.cleared:continue
            q=t.safe_clear_point(self.robot.position)
            if q is None:
                q=t.next_point(np.asarray(self.robot.position)) if getattr(self,'cover_target_entry',False) else t.center
            targets.append(('target',c,np.asarray(q)))
        unknown=self.unknown()
        if not unknown:return targets
        actual=self.coverage.covered[unknown[0]]
        # Targets are mandatory route vertices but optional sensing sites.
        points=[n[2].copy() for n in targets]+[np.array(p) for p in self.anchors]
        n_target=len(targets)
        active=np.ones(len(points),dtype=bool)
        present=np.ones(len(points),dtype=bool)
        masks=[self.coverage.mask(p) for p in points]
        start=np.asarray(self.robot.position)
        def route_order():
            indices=[i for i in range(len(points)) if present[i]]
            return [indices[j] for j in open_route(start,[points[i] for i in indices])]
        def total_without(i):
            total=actual.copy()
            for j in range(len(points)):
                if j!=i and active[j]:total|=masks[j]
            return total
        def prune():
            while True:
                order=route_order();gains=[]
                for k,i in enumerate(order):
                    if not active[i]:continue
                    gain=30*len(unknown)
                    if i>=n_target:
                        a=start if k==0 else points[order[k-1]]
                        gain+=np.linalg.norm(points[i]-a)
                        if k+1<len(order):
                            b=points[order[k+1]]
                            gain+=np.linalg.norm(points[i]-b)-np.linalg.norm(a-b)
                    gains.append((gain,i))
                removed=False
                for gain,i in sorted(gains,reverse=True):
                    if np.all(total_without(i)):
                        active[i]=False
                        if i>=n_target:present[i]=False
                        removed=True;break
                if not removed:break
        prune()
        if self.merge_stations:
            def full_cost(candidate_points,candidate_present,candidate_active):
                indices=np.flatnonzero(candidate_present)
                order=open_route(start,[candidate_points[i] for i in indices])
                p=start;value=30*len(unknown)*int(np.count_nonzero(candidate_active))
                for j in order:
                    q=candidate_points[indices[j]];value+=np.linalg.norm(q-p);p=q
                return float(value)
            for merge_iteration in range(4):
                old_cost=full_cost(points,present,active);best=None
                selected=[i for i in range(0 if self.merge_target_scans else n_target,len(points)) if active[i]]
                for at,i in enumerate(selected):
                    for j in selected[:at]:
                        remaining=actual.copy()
                        for k in range(len(points)):
                            if active[k] and k not in [i,j]:remaining|=masks[k]
                        needed=self.coverage.centers[~remaining]
                        if not len(needed):continue
                        h=self.coverage.half
                        corners=np.vstack([needed+np.array([x*h,y*h]) for x,y in [(-1,-1),(-1,1),(1,-1),(1,1)]])
                        hull=corners[ConvexHull(corners).vertices]
                        if diameter(hull)[0]>1999.9799:continue
                        center,radius,_=enclosing_circle(hull)
                        if radius>999.98999:continue
                        new_points=points+[center]
                        new_present=np.append(present,True);new_active=np.append(active,True)
                        for removed in [i,j]:
                            if removed>=n_target:new_present[removed]=False
                            new_active[removed]=False
                        value=full_cost(new_points,new_present,new_active)
                        if value<old_cost-1e-6 and (best is None or value<best[0]):
                            best=(value,i,j,center,new_points,new_present,new_active)
                if best is None:break
                value,i,j,center,points,present,active=best
                masks.append(self.coverage.mask(center))
                self.robot.record(dict(kind='merge_scans',point=center.tolist(),removed=[int(i),int(j)],
                    predicted_saving_s=(old_cost-value)/5,proof='MEC of all responsibility-cell corners <= 999.99 m'))
                prune()
        for _ in range(self.cover_sweeps):
            order=route_order()
            improvement=0.
            for k,i in enumerate(order):
                if i<n_target or not active[i]:continue
                needed=self.coverage.centers[~total_without(i)]
                if not len(needed):continue
                h=self.coverage.half
                corners=np.vstack([needed+np.array([x*h,y*h]) for x,y in [(-1,-1),(-1,1),(1,-1),(1,1)]])
                witnesses=corners[ConvexHull(corners).vertices]/1000
                before=points[i]/1000
                previous=(start if k==0 else points[order[k-1]])/1000
                following=points[order[k+1]]/1000 if k+1<len(order) else None
                def objective(q):
                    value=np.sqrt(np.dot(q-previous,q-previous)+1e-16)
                    if following is not None:value+=np.sqrt(np.dot(q-following,q-following)+1e-16)
                    return float(value)
                def gradient(q):
                    value=(q-previous)/max(np.linalg.norm(q-previous),1e-8)
                    if following is not None:value+=(q-following)/max(np.linalg.norm(q-following),1e-8)
                    return value
                cons={'type':'ineq','fun':lambda q: .99998999**2-np.sum((q-witnesses)**2,axis=1),
                      'jac':lambda q:-2*(q-witnesses)}
                sol=minimize(objective,before,jac=gradient,constraints=cons,method='SLSQP',
                             options={'ftol':1e-10,'maxiter':60})
                if np.max(np.linalg.norm(witnesses-sol.x,axis=1))<=.99999 and objective(sol.x)<=objective(before)+1e-8:
                    improvement+=objective(before)-objective(sol.x)
                    points[i]=sol.x*1000;masks[i]=self.coverage.mask(points[i])
            prune()
            if improvement<1e-5:break
        union=actual.copy()
        for i in range(len(points)):
            if active[i]:union|=masks[i]
        if not np.all(union):raise ArithmeticError('Relocated cover lost cells')
        scans=[('scan',-100-i,points[i]) for i in range(len(points)) if active[i]]
        nodes=targets+scans
        self.cover_targets=set()
        return nodes
