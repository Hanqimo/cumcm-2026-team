"""Whole-service routing, rotated cover plans and paid measurements in transit."""
import copy,math
import numpy as np
from combined_cost_cover import CombinedCostCoverPlanner
from flexible_cover import FlexibleCoverPlanner
from joint_strategies import open_route


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
                 probe_gain=100.,probe_min_radius=100.,cover_radii=None,initial_design=False,cover_target_entry=False,**kwargs):
        super().__init__(robot,**kwargs)
        self.service_route=service_route;self.cover_trials=cover_trials
        self.transit_probes=transit_probes;self.probe_gain=probe_gain
        self.probe_min_radius=probe_min_radius;self.pending_probe=None
        self.cover_radii=cover_radii;self.initial_design=initial_design
        self.initial_designed=False
        self.cover_target_entry=cover_target_entry

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

    def candidates(self):
        original=self.anchors;radius=math.hypot(*original[1]);best=None
        try:
            for trial in range(self.cover_trials*len(self.cover_radii or [radius])):
                radius=(self.cover_radii or [radius])[trial//self.cover_trials]
                rotation=trial%self.cover_trials
                angle=math.pi/3*rotation/self.cover_trials
                self.anchors=[(0.,0.)]+[(radius*math.cos(angle+i*math.pi/3),radius*math.sin(angle+i*math.pi/3)) for i in range(6)]
                cover=np.zeros(len(self.coverage.centers),dtype=bool)
                for p in self.anchors:cover|=self.coverage.mask(p)
                if not np.all(cover):continue
                nodes=FlexibleCoverPlanner.candidates(self)
                if not nodes:continue
                order,cost=self.route(nodes)
                score=cost+30*len(self.unknown())*sum(n[0]=='scan' for n in nodes)
                if best is None or score<best[0]:best=(score,nodes,order)
        finally:self.anchors=original
        if best is None:return []
        _,nodes,order=best;first=nodes[order[0]]
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
