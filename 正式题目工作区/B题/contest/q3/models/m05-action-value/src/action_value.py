"""Observation-only action values, with persistent nonconvex optical exclusions.

Scenario averages are planning heuristics, never completion certificates.
Actual safety continues to use an outer region and paid API actions.
"""
import copy
import math
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.geometry.polygon import orient
from bearing_geometry import enclosing_circle, diameter
from legacy_strategy import Track, CLEAR_RADIUS
from service_routing import ServicePlanner
from cost_aware import reception_safe


class OpticalTrack(Track):
    def sync_region(self):
        polygon=Polygon(self.poly)
        self.feasible=polygon if not hasattr(self,'feasible') else self.feasible.intersection(polygon)
        self.refresh()

    def refresh(self):
        if self.feasible.is_empty or self.feasible.area<1e-14:
            raise ArithmeticError('Optical feasible region empty or numerically degenerate')
        self.poly=np.asarray(orient(self.feasible.convex_hull,sign=1.).exterior.coords[:-1])
        self.center,self.radius,_=enclosing_circle(self.poly)

    def update(self,point,observation):
        super().update(point,observation)
        self.sync_region()

    def exclude_clear(self,point):
        # Inscribed polygon is strictly inside the physical failed-clear disk.
        # Its removal keeps a conservative OUTER set, including boundary margin.
        self.feasible=self.feasible.difference(Point(point).buffer(19.999,quad_segs=16))
        self.refresh()


def clone_track(track):
    t=copy.copy(track);t.poly=track.poly.copy();t.history=list(track.history)
    return t  # Shapely geometries are immutable.


def scenarios(track,count=3):
    region=getattr(track,'feasible',Polygon(track.poly))
    _,(i,j)=diameter(track.poly);a,b=track.poly[i],track.poly[j]
    points=[]
    for f in np.linspace(.15,.85,count):
        q=(1-f)*a+f*b
        q=.95*q+.05*np.asarray(region.representative_point().coords[0])
        if region.covers(Point(q)):points.append(q)
    if len(points)<count:
        pieces=list(region.geoms) if hasattr(region,'geoms') else [region]
        for piece in sorted(pieces,key=lambda g:g.area,reverse=True):
            points.append(np.asarray(piece.representative_point().coords[0]))
            if len(points)>=count:break
    return points


def synthetic_observation(q,truth,error):
    if np.linalg.norm(truth-q)<=5:return dict(measure_result='near')
    angle=math.degrees(math.atan2(truth[1]-q[1],truth[0]-q[0]))
    return dict(measure_result='direction',svd_deg=round((angle+error)%360,2)%360)


def finish_cost(track,start,truth,error,first=None,exit_point=None):
    """Bounded rollout of the unchanged geometric completion module in seconds."""
    t=clone_track(track);p=np.asarray(start);cost=0.
    for k in range(5):
        q=t.safe_clear_point(p)
        if q is not None:
            cost+=np.linalg.norm(q-p)/5+5
            if exit_point is not None:cost+=np.linalg.norm(q-exit_point)/5
            return float(cost)
        q=first if k==0 and first is not None else t.next_point(p)
        cost+=np.linalg.norm(q-p)/5+6  # Conservative switch allowance in planning.
        t.update(q,synthetic_observation(q,truth,error));p=q
    return float(cost+1000)


class ActionValuePlanner(ServicePlanner):
    def __init__(self,robot,*,optical=True,optical_radius=65.,optical_margin=1.,
                 optical_update=True,optical_risk=.2,optical_max_trials=2,
                 value_probes=False,value_margin=3.,**kwargs):
        super().__init__(robot,**kwargs)
        self.optical=optical;self.optical_radius=optical_radius
        self.optical_margin=optical_margin;self.optical_update=optical_update
        self.optical_risk=optical_risk;self.optical_max_trials=optical_max_trials
        self.value_probes=value_probes;self.value_margin=value_margin
        self.optical_attempts={}

    def observe(self,point,channel):
        result=super().observe(point,channel)
        if channel in self.tracks:
            t=self.tracks[channel]
            if not isinstance(t,OpticalTrack):t.__class__=OpticalTrack
            t.sync_region()
            self.robot.record(dict(kind='optical_region',channel=channel,
                wkt=t.feasible.wkt,vertices=t.poly.tolist(),radius_m=t.radius))
        return result

    def aggregate(self,values):
        return float((1-self.optical_risk)*np.mean(values)+self.optical_risk*np.max(values))

    def optical_action(self,t):
        if not self.optical or not CLEAR_RADIUS<t.radius<=self.optical_radius:return None
        if len(self.optical_attempts.get(t.channel,[]))>=self.optical_max_trials:return None
        start=np.asarray(self.robot.position);samples=scenarios(t)
        states=[(x,e) for x in samples for e in [-1.,0.,1.]]
        baseline=self.aggregate([finish_cost(t,start,x,e) for x,e in states])
        candidates=[start,t.center]
        d=start-t.center;length=np.linalg.norm(d)
        if length>1e-8:candidates.append(t.center+d/length*min(15.,t.radius*.35))
        _,(i,j)=diameter(t.poly)
        if t.radius>35:
            candidates.extend([.65*t.center+.35*t.poly[i],.65*t.center+.35*t.poly[j]])
        best=None
        for q in candidates:
            if any(math.dist(q,p)<2. for p in self.optical_attempts.get(t.channel,[])):continue
            covered=t.feasible.intersection(Point(q).buffer(19.999,quad_segs=16)).area
            if covered<.12*t.feasible.area:continue
            failed=clone_track(t)
            try:
                if self.optical_update:failed.exclude_clear(q)
            except ArithmeticError:continue
            values=[]
            for x,e in states:
                value=np.linalg.norm(q-start)/5
                if np.linalg.norm(x-q)<=20:value+=5
                else:value+=3+finish_cost(failed,q,x,e)
                values.append(value)
            score=self.aggregate(values)
            if score<baseline-self.optical_margin and (best is None or score<best[0]):
                best=(score,q,baseline,covered/t.feasible.area)
        return best

    def solve_track(self,track):
        for _ in range(20):
            self.robot.check_budget();track=self.tracks[track.channel]
            if track.radius<=CLEAR_RADIUS:return super().solve_track(track)
            proposal=self.optical_action(track)
            if proposal is not None:
                score,q,baseline,fraction=proposal
                self.robot.record(dict(kind='optical_decision',channel=track.channel,point=q.tolist(),
                    predicted_s=score,radio_predicted_s=baseline,area_fraction=fraction))
                self.optical_attempts.setdefault(track.channel,[]).append(q.tolist())
                if self.robot.clear(tuple(q),track.channel):return
                if self.optical_update:track.exclude_clear(q)
                self.robot.record(dict(kind='optical_failure_update',channel=track.channel,
                    point=q.tolist(),wkt=track.feasible.wkt,vertices=track.poly.tolist(),radius_m=track.radius))
                continue
            q=track.next_point(np.asarray(self.robot.position))
            if self.observe(q,track.channel)['measure_result']=='no_signal':
                raise ArithmeticError('Certified radio point returned no signal')
        raise RuntimeError('Action-value localization budget exhausted')

    def probe_on_leg(self,node):
        if not self.value_probes:return super().probe_on_leg(node)
        start=np.asarray(self.robot.position);end=np.asarray(node[2])
        if node[0]=='target':
            tr=self.tracks[node[1]];safe=tr.safe_clear_point(start)
            end=safe if safe is not None else tr.next_point(start)
        if np.linalg.norm(end-start)<250:return None
        tracks=[t for c,t in self.tracks.items() if c not in self.robot.cleared and t.radius>40]
        tracks=sorted(tracks,key=lambda t:np.linalg.norm(t.center-end))[:3]
        baselines={}
        for t in tracks:
            states=[(x,e) for x in scenarios(t) for e in [-1.,0.,1.]]
            baselines[t.channel]=(states,self.aggregate([finish_cost(t,end,x,e) for x,e in states]))
        best=None
        for fraction in [.25,.5,.75]:
            q=start+fraction*(end-start);channels=[];net=0.
            for t in tracks:
                if not reception_safe(t,q):continue
                if min(math.dist(q,h['position']) for h in t.history)<150:continue
                if math.dist(q,self.attempts.get(t.channel,(1e9,1e9)))<150:continue
                states,before=baselines[t.channel];values=[]
                for x,e in states:
                    after=clone_track(t);after.update(q,synthetic_observation(q,x,e))
                    values.append(finish_cost(after,end,x,e))
                saving=before-self.aggregate(values)-6
                if saving>self.value_margin:channels.append(t.channel);net+=saving
            if channels and (best is None or net>best[0]):best=(net,q,channels)
        if best:
            self.robot.record(dict(kind='value_bundle',point=best[1].tolist(),channels=best[2],predicted_saving_s=best[0]))
        return None if best is None else best[1:]
