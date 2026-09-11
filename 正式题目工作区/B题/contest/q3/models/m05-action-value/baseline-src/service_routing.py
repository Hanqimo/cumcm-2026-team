"""Whole-service routing, rotated cover plans and paid measurements in transit."""
import copy,math
import numpy as np
from combined_cost_cover import CombinedCostCoverPlanner
from flexible_cover import FlexibleCoverPlanner
from joint_strategies import open_route
from voronoi_coverage import HybridCoverage,covering_radius


def directed_route(start,nodes,tracks,restarts=3):
    exits=[np.asarray(start)]+[np.asarray(tracks[n[1]].center if n[0]=='target' else n[2]) for n in nodes]
    size=len(nodes);D=np.zeros((size+1,size+1))
    for i,p in enumerate(exits):
        for j,(kind,c,q) in enumerate(nodes,1):
            if i==j:continue
            entry=q
            if kind=='target':
                tr=tracks[c];safe=tr.safe_clear_point(p)
                entry=safe if safe is not None else tr.next_point(p)
            D[i,j]=np.linalg.norm(entry-p)+np.linalg.norm(exits[j]-entry)
    def value(r):return float(sum(D[a,b] for a,b in zip(r,r[1:])))
    best=None
    for restart in range(min(restarts,size)):
        left=set(range(1,size+1));r=[0]
        first=sorted(left,key=lambda j:D[0,j])[restart];r.append(first);left.remove(first)
        while left:
            j=min(left,key=lambda j:D[r[-1],j]);r.append(j);left.remove(j)
        for _ in range(25):
            old=value(r);chosen=None
            for i in range(1,len(r)-1):
                for j in range(i+1,len(r)):
                    trial=r[:i]+list(reversed(r[i:j+1]))+r[j+1:];v=value(trial)
                    if v<old-1e-7:old,chosen=v,trial
            if chosen is None:break
            r=chosen
        val=value(r)
        if best is None or val<best[0]:best=(val,r)
    return [j-1 for j in best[1][1:]],best[0]


class ServicePlanner(CombinedCostCoverPlanner):
    def __init__(self,robot,*,service_route=False,cover_trials=1,transit_probes=False,
                 probe_gain=100.,probe_min_radius=100.,cover_radii=None,initial_design=False,cover_target_entry=False,target_estimator='mec',merge_trials=False,warm_cover=False,hybrid_cover=False,continuous_stop=False,**kwargs):
        super().__init__(robot,**kwargs)
        self.service_route=service_route;self.cover_trials=cover_trials
        self.transit_probes=transit_probes;self.probe_gain=probe_gain
        self.probe_min_radius=probe_min_radius;self.pending_probe=None
        self.cover_radii=cover_radii;self.initial_design=initial_design
        self.initial_designed=False
        self.cover_target_entry=cover_target_entry
        self.target_estimator=target_estimator;self.merge_trials=merge_trials
        self.warm_cover=warm_cover;self.warm_scans=[]
        self.hybrid_cover=hybrid_cover
        if hybrid_cover or continuous_stop:self.coverage=HybridCoverage()

    def target_position(self,tr):
        if self.target_estimator=='mec':return tr.center
        v=tr.poly-tr.center;u=np.roll(v,-1,axis=0)
        cross=v[:,0]*u[:,1]-u[:,0]*v[:,1]
        center=tr.center+np.sum((v+u)*cross[:,None],axis=0)/(3*cross.sum()) if abs(cross.sum())>1e-10 else tr.center
        if self.target_estimator=='wls':
            A=[];b=[]
            for h in tr.history:
                if h['measure_result']!='direction':continue
                angle=math.radians(h['svd_deg']);p=np.asarray(h['position'])
                normal=np.array([-math.sin(angle),math.cos(angle)])/max(10,np.linalg.norm(center-p))
                A.append(normal);b.append(np.dot(normal,p))
            if len(A)>=2:
                estimate=np.linalg.lstsq(np.asarray(A),np.asarray(b),rcond=None)[0]
                edges=np.roll(tr.poly,-1,axis=0)-tr.poly;delta=estimate-tr.poly
                if np.all(edges[:,0]*delta[:,1]-edges[:,1]*delta[:,0]>=-1e-7):center=estimate
        return center

    def design_initial_point(self):
        original_radius=self.initial_baseline;best=None
        for radius in [250.,450.,650.]:
            for angle in np.linspace(0,2*math.pi,12,endpoint=False):
                q=radius*np.array([math.cos(angle),math.sin(angle)]);centers=[];uncertainty=0.
                for tr in self.tracks.values():
                    if np.linalg.norm(q-tr.center)>1000:
                        centers.append(tr.center);uncertainty+=tr.radius;continue
                    bearing=math.degrees(math.atan2(tr.center[1]-q[1],tr.center[0]-q[0]))
                    radii=[];cs=[]
                    for error in [-1.,0.,1.]:
                        temporary=copy.copy(tr);temporary.history=list(tr.history);temporary.poly=tr.poly.copy()
                        temporary.update(q,dict(measure_result='direction',svd_deg=round((bearing+error)%360,2)))
                        radii.append(temporary.radius);cs.append(temporary.center)
                    centers.append(np.mean(cs,axis=0));uncertainty+=np.mean(radii)
                points=centers+[np.asarray(p) for p in self.anchors[1:]]
                order=open_route(q,points);p=q;score=radius+uncertainty
                for i in order:score+=np.linalg.norm(points[i]-p);p=points[i]
                if best is None or score<best[0]:best=(score,q)
        return best[1]

    def route(self,nodes):
        if self.service_route:return directed_route(self.robot.position,nodes,self.tracks)
        order=open_route(self.robot.position,[n[2] for n in nodes],restarts=self.route_restarts)
        p=np.asarray(self.robot.position);cost=0.
        for i in order:cost+=np.linalg.norm(nodes[i][2]-p);p=nodes[i][2]
        return order,float(cost)

    def probe_on_leg(self,node):
        start=np.asarray(self.robot.position);end=node[2]
        if node[0]=='target':
            tr=self.tracks[node[1]];safe=tr.safe_clear_point(start)
            end=safe if safe is not None else tr.next_point(start)
        if np.linalg.norm(end-start)<250:return None
        best=None
        for f in [.25,.5,.75]:
            q=start+f*(end-start);channels=[];benefit=0.
            for c,tr in self.tracks.items():
                if c in self.robot.cleared or tr.radius<self.probe_min_radius:continue
                if min(math.dist(q,h['position']) for h in tr.history)<150:continue
                if math.dist(q,self.attempts.get(c,(1e9,1e9)))<150:continue
                if np.linalg.norm(q-tr.center)>1000:continue
                radii=[]
                angle=math.degrees(math.atan2(tr.center[1]-q[1],tr.center[0]-q[0]))
                for error in [-1.,0.,1.]:
                    temporary=copy.copy(tr);temporary.history=list(tr.history);temporary.poly=tr.poly.copy()
                    temporary.update(q,dict(measure_result='direction',svd_deg=round((angle+error)%360,2)))
                    radii.append(temporary.radius)
                gain=tr.radius-float(np.mean(radii))
                if gain>=self.probe_gain:channels.append(c);benefit+=gain-30
            if channels and (best is None or benefit>best[0]):best=(benefit,q,channels)
        return None if best is None else best[1:]

    def plan(self):
        original=self.anchors;radius=math.hypot(*original[1]);best=None;original_merge=self.merge_stations
        try:
            for trial in range(self.cover_trials*len(self.cover_radii or [radius])):
                radius=(self.cover_radii or [radius])[trial//self.cover_trials]
                rotation=trial%self.cover_trials
                angle=math.pi/3*rotation/self.cover_trials
                self.anchors=[(0.,0.)]+[(radius*math.cos(angle+i*math.pi/3),radius*math.sin(angle+i*math.pi/3)) for i in range(6)]
                cover=np.zeros(len(self.coverage.centers),dtype=bool)
                for p in self.anchors:cover|=self.coverage.mask(p)
                if not np.all(cover) and not (self.hybrid_cover and covering_radius(self.anchors)[0]<=999.98):continue
                for merged in ([False,True] if self.merge_trials else [original_merge]):
                    self.merge_stations=merged
                    nodes=FlexibleCoverPlanner.candidates(self)
                    if not nodes:continue
                    order,cost=self.route(nodes)
                    score=cost+30*len(self.unknown())*sum(n[0]=='scan' for n in nodes)
                    if best is None or score<best[0]:best=(score,nodes,order)
            if self.warm_cover and self.warm_scans:
                self.anchors=original+[tuple(p) for p in self.warm_scans]
                self.merge_stations=original_merge
                nodes=FlexibleCoverPlanner.candidates(self)
                if nodes:
                    order,cost=self.route(nodes)
                    score=cost+30*len(self.unknown())*sum(n[0]=='scan' for n in nodes)
                    if best is None or score<best[0]:best=(score,nodes,order)
        finally:self.anchors=original;self.merge_stations=original_merge
        return best

    def candidates(self):
        best=self.plan();self.last_plan=best
        if best is None:return []
        _,nodes,order=best;first=nodes[order[0]]
        if self.warm_cover:self.warm_scans=[n[2].copy() for n in nodes if n[0]=='scan']
        # A planned scan at the target point must happen before a moving solve.
        if first[0]=='target':
            match=[n for n in nodes if n[0]=='scan' and math.dist(n[2],first[2])<1e-5]
            if match:first=match[0]
        if self.transit_probes:
            probe=self.probe_on_leg(first)
            if probe is not None:
                self.pending_probe=probe
                return [('scan',-9999,probe[0])]
        return [first]

    def at_site_scan(self,point,force=False):
        if self.initial_design and not self.initial_designed and self.iterations==0 and np.linalg.norm(point)>.1:
            point=self.design_initial_point();self.initial_designed=True
            self.robot.record(dict(kind='initial_design',point=point.tolist()))
        if force and self.pending_probe is not None and math.dist(point,self.pending_probe[0])<1e-6:
            q,channels=self.pending_probe;self.pending_probe=None
            self.robot.record(dict(kind='transit_probe',point=q.tolist(),channels=channels))
            for c in sorted(channels,key=lambda c:(c!=self.robot.channel,c)):self.observe(q,c)
            return
        return super().at_site_scan(point,force=force)

    def certificate(self):
        result=super().certificate()
        if isinstance(self.coverage,HybridCoverage):
            result['exact_disk_cover']={str(c):dict(max_nearest_distance_m=self.coverage.exact_status(self.coverage.samples[c])[0],
                witness=self.coverage.exact_status(self.coverage.samples[c])[1].tolist(),accepted_by_grid=bool(np.all(self.coverage.covered[c]))) for c in result['absent_channels']}
        return result


class TransitSearchPlanner(ServicePlanner):
    def __init__(self,robot,*,search_margin_s=10.,search_bonus=0.,**kwargs):
        super().__init__(robot,**kwargs)
        self.search_margin_s=search_margin_s;self.search_bonus=search_bonus

    def candidates(self):
        nodes=super().candidates();unknown=self.unknown()
        if not nodes or not unknown or self.pending_probe is not None:return nodes
        first=nodes[0];p=np.asarray(self.robot.position);q=first[2]
        if first[0]=='target':
            tr=self.tracks[first[1]];safe=tr.safe_clear_point(p)
            q=safe if safe is not None else tr.next_point(p)
        if np.linalg.norm(q-p)<350:return nodes
        previous=self.coverage.covered[unknown].copy();old_position=self.robot.position
        before=self.last_plan[0];best=None
        try:
            for fraction in [.33,.67]:
                probe=p+fraction*(q-p);mask=self.coverage.mask(probe)
                gain=float(np.mean(mask&~previous[0]))
                if gain<.015:continue
                self.coverage.covered[unknown]=previous|mask
                self.robot.position=tuple(probe)
                after=self.plan()
                if after is None:continue
                cost=np.linalg.norm(probe-p)+30*len(unknown)+after[0]
                hidden=max(0,13-len(self.robot.discovered))
                bonus=self.search_bonus*hidden*gain/max(.05,float(np.mean(~previous[0])))
                saving=(before-cost+bonus)/5
                if saving>self.search_margin_s and (best is None or saving>best[0]):best=(saving,probe,gain)
        finally:
            self.coverage.covered[unknown]=previous;self.robot.position=old_position
        if best is not None:
            self.robot.record(dict(kind='transit_search_plan',point=best[1].tolist(),predicted_saving_s=best[0],new_coverage_fraction=best[2],planning_only=True))
            return [('scan',-9998,best[1])]
        return nodes
