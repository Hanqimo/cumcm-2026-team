"""Independent candidate families for P3; all maintain the same clear certificate."""
import math
import numpy as np
from scipy.spatial import ConvexHull
from legacy_strategy import Planner as BasePlanner, CLEAR_RADIUS, Track
from bearing_geometry import enclosing_circle


def exclude_disk_hull(poly, center, radius=999.9):
    """Convex outer hull of P outside a disk (uses P-boundary candidates).

    A maximum of a linear functional over P minus an open disk is attained
    at an outside vertex or an edge/circle crossing; the inner arc is concave.
    Shrink the excluded radius by .1 m to protect floating-point intersections.
    """
    center=np.asarray(center);points=[]
    for i,p in enumerate(poly):
        q=poly[(i+1)%len(poly)];v=q-p;offset=p-center
        if np.dot(offset,offset)>=radius**2:points.append(p)
        a=float(np.dot(v,v));b=2*float(np.dot(v,offset));c=float(np.dot(offset,offset)-radius**2)
        disc=b*b-4*a*c
        if a>1e-18 and disc>=0:
            for t in [(-b-math.sqrt(disc))/(2*a),(-b+math.sqrt(disc))/(2*a)]:
                if 0<=t<=1:points.append(p+t*v)
    if not points:raise ArithmeticError('Negative measurement contradicts region')
    points=np.unique(np.round(np.asarray(points),9),axis=0)
    if len(points)<3:return points
    try:return points[ConvexHull(points).vertices]
    except Exception:
        low,high=points.min(axis=0)-1e-7,points.max(axis=0)+1e-7
        return np.array([low,[high[0],low[1]],high,[low[0],high[1]]])


def open_route(start, points, end=None, restarts=1):
    """Nearest-neighbour initialization + open-path 2-opt, fixed start, free end."""
    if not len(points):
        return []
    pts = np.vstack([start, points])
    D = np.linalg.norm(pts[:, None] - pts[None, :], axis=2)
    end_cost=np.zeros(len(pts)) if end is None else np.linalg.norm(pts-end,axis=1)
    def length(route):return float(sum(D[a,b] for a,b in zip(route,route[1:]))+end_cost[route[-1]])
    rng=np.random.default_rng(42)
    best_route,best_length=None,float('inf')
    for restart in range(restarts):
        left = set(range(1, len(pts)))
        route = [0]
        if restart:
            first=sorted(left,key=lambda j:D[0,j])[(restart-1)%len(left)]
            route.append(first);left.remove(first)
        while left:
            q = min(left, key=lambda j: D[route[-1], j])
            route.append(q);left.remove(q)
        for _ in range(50):
            gain, best = 1e-8, None
            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    old = D[route[i-1], route[i]]
                    new = D[route[i-1], route[j]]
                    if j + 1 < len(route):
                        old += D[route[j], route[j+1]]
                        new += D[route[i], route[j+1]]
                    else:
                        old += end_cost[route[j]]
                        new += end_cost[route[i]]
                    if old - new > gain:
                        gain, best = old-new, (i, j)
            if best is not None:
                i,j=best;route[i:j+1]=reversed(route[i:j+1]);continue
            if restarts>1:
                old_length=length(route);replacement=None
                for i in range(1,len(route)):
                    reduced=route[:i]+route[i+1:]
                    for j in range(1,len(route)):
                        trial=reduced[:j]+[route[i]]+reduced[j:]
                        value=length(trial)
                        if value<old_length-1e-7:
                            old_length,replacement=value,trial
                if replacement is not None:route=replacement;continue
            break
        value=length(route)
        if value<best_length:best_length,best_route=value,route
    return [i-1 for i in best_route[1:]]


class JointPlanner(BasePlanner):
    def __init__(self, robot, *, family='joint', scan_gain=.05, info_distance=150.,
                 initial_baseline=0., route_on=True, info_radius=60., info_maxobs=2,
                 anchor_radius=1350., initial_force=True, initial_rotation=0., negative_regions=False,
                 cover_move_weight=1., grid_step=450., one_step=False, probe_length=0., route_bias=0.,route_restarts=1):
        super().__init__(robot)
        self.family = family
        self.scan_gain = scan_gain
        self.info_distance = info_distance
        self.initial_baseline = initial_baseline
        self.route_on = route_on
        self.info_radius = info_radius
        self.info_maxobs = info_maxobs
        self.attempts = {}
        self.anchors = [(0.,0.)]+[(anchor_radius*math.cos(i*math.pi/3),anchor_radius*math.sin(i*math.pi/3)) for i in range(6)]
        self.initial_force,self.initial_rotation=initial_force,initial_rotation
        self.negative_regions=negative_regions
        self.cover_move_weight=cover_move_weight
        self.grid_step=grid_step
        self.static_cover=None
        self.cover_targets=set()
        self.one_step=one_step
        self.probe_length,self.route_bias=probe_length,route_bias
        self.route_restarts=route_restarts
        self.iterations = 0

    def unknown(self):
        if len(self.robot.discovered)==16:return []
        return super().unknown()

    def solve_track(self,track):
        if self.probe_length and len(track.history)==1 and track.history[0]['measure_result']=='direction':
            first=track.history[0];s=np.asarray(first['position']);a=math.radians(first['svd_deg'])
            u=np.array([math.cos(a),math.sin(a)]);v=np.array([-math.sin(a),math.cos(a)])
            length=self.probe_length
            forward=max(.35*length,length*length/1900+length*.018)
            lateral=math.sqrt(length*length-forward*forward)
            choices=[s+forward*u+lateral*v,s+forward*u-lateral*v]
            q=min(choices,key=lambda q:math.dist(q,self.robot.position))
            if self.observe(q,track.channel)['measure_result']=='no_signal':
                raise ArithmeticError('Q2 short-baseline reception certificate failed')
            if self.one_step:return
        if not self.one_step or track.radius <= CLEAR_RADIUS:
            return super().solve_track(track)
        q=track.next_point(np.asarray(self.robot.position))
        if self.observe(q,track.channel)['measure_result']=='no_signal':
            raise ArithmeticError('Guaranteed next observation lost reception')

    def observe(self, point, channel):
        if not self.negative_regions:
            result = super().observe(point, channel)
        else:
            point=tuple(float(v) for v in point)
            result=self.robot.measure(point,channel)
            if result['measure_result']=='no_signal':self.coverage.add(channel,point)
            else:
                track=self.tracks.setdefault(channel,Track(channel))
                track.update(point,result)
            if channel in self.tracks:
                track=self.tracks[channel]
                for p in self.coverage.samples[channel]:
                    track.poly=exclude_disk_hull(track.poly,p)
                track.center,track.radius,_=enclosing_circle(track.poly)
                self.robot.record(dict(kind='region',channel=channel,position=list(point),
                    radius_m=track.radius,center=track.center.tolist(),vertices=track.poly.tolist(),
                    observations=len(track.history),negative_positions=self.coverage.samples[channel]))
        self.attempts[channel] = tuple(point)
        return result

    def at_site_scan(self, point, force=False):
        """Unknown scans buy coverage; known scans buy intersecting bearings."""
        unknown = self.unknown()
        channels = set(unknown if force or self.coverage.gain(point, unknown) >= self.scan_gain else [])
        for c, track in self.tracks.items():
            if c in self.robot.cleared or track.radius <= self.info_radius or len(track.history) >= self.info_maxobs:
                continue
            if c in self.attempts and math.dist(point,self.attempts[c]) < self.info_distance:
                continue
            if min(math.dist(point, h['position']) for h in track.history) >= self.info_distance:
                # No-signal is allowed for batch measurements; never corrupt P.
                channels.add(c)
        if channels:
            self.robot.scanned_sites += 1
        for c in sorted(channels, key=lambda c: (c != self.robot.channel, c)):
            self.observe(point, c)

    def candidates(self):
        pending = [t for c,t in self.tracks.items() if c not in self.robot.cleared]
        nodes = []
        for t in pending:
            q = t.safe_clear_point(self.robot.position)
            q = t.center if q is None else q
            if self.route_bias and len(t.history)==1:
                q=q+self.route_bias*(q-np.asarray(t.history[0]['position']))
            nodes.append(('target', t.channel, np.asarray(q)))
        unknown = self.unknown()
        if not unknown:
            return nodes
        if self.family == 'adaptive':
            return self.adaptive_cover(nodes,unknown)
        # Keep a conservative fallback cover from original anchors. We may
        # anticipate target visits for route scoring, but stopping uses real scans.
        covered = self.coverage.covered[unknown[0]].copy()
        if self.family != 'anchors':
            for _, _, q in nodes:
                covered |= self.coverage.mask(q)
        anchors = [(i,p,self.coverage.mask(p)) for i,p in enumerate(self.anchors)]
        needed = []
        while not np.all(covered):
            if not anchors:
                raise RuntimeError('Search fallback cover exhausted')
            # Greedy set cover only selects waypoints; it does not certify absence.
            a = max(anchors, key=lambda a: int(np.count_nonzero(a[2] & ~covered)))
            gain = np.count_nonzero(a[2] & ~covered)
            if not gain:
                raise RuntimeError('No progress in waypoint cover')
            needed.append(('scan', a[0], np.asarray(a[1])))
            covered |= a[2]
            anchors.remove(a)
        return nodes + needed

    def adaptive_cover(self,nodes,unknown):
        def bits(mask):
            return int.from_bytes(np.packbits(mask,bitorder='little').tobytes(),'little')
        if self.static_cover is None:
            pts=[np.array(p) for p in self.anchors]
            pts += [np.array([x,y]) for x in np.arange(-1350,1351,self.grid_step)
                    for y in np.arange(-1350,1351,self.grid_step) if math.hypot(x,y)<=1750]
            self.static_cover=[(q,bits(self.coverage.mask(q))) for q in pts]
        covered=bits(self.coverage.covered[unknown[0]])
        full=(1<<len(self.coverage.centers))-1
        p=np.asarray(self.robot.position)
        route=open_route(p,[n[2] for n in nodes])
        route_points=[p]+[nodes[i][2] for i in route]
        # Marginal route insertion distance, not straight distance from dog.
        def detour(q):
            best=float(np.linalg.norm(route_points[-1]-q))
            for a,b in zip(route_points,route_points[1:]):
                best=min(best,float(np.linalg.norm(a-q)+np.linalg.norm(q-b)-np.linalg.norm(a-b)))
            return max(0.,best)
        candidates=[('scan',-1,p,bits(self.coverage.mask(p)),0.)]
        candidates += [(kind,c,q,bits(self.coverage.mask(q)),0.) for kind,c,q in nodes]
        candidates += [('scan',i,q,mask,detour(q)) for i,(q,mask) in enumerate(self.static_cover)]
        needed=[];self.cover_targets=set()
        while covered != full:
            missing=full^covered
            best=max(candidates,key=lambda a:(a[3]&missing).bit_count()/(6*len(unknown)+self.cover_move_weight*a[4]/5))
            if not best[3]&missing:raise RuntimeError('Adaptive cover cannot close remaining cells')
            covered |= best[3]
            kind,c,q,mask,d=best
            if kind=='target':self.cover_targets.add(c)
            else:needed.append((kind,c,q))
            candidates.remove(best)
        return nodes+needed

    def run(self):
        self.at_site_scan((0.,0.), force=True)
        if self.initial_baseline:
            pending = list(self.tracks.values())
            angle = (math.atan2(pending[0].center[1], pending[0].center[0]) if pending else 0.)+math.radians(self.initial_rotation)
            q = np.array([math.cos(angle),math.sin(angle)]) * self.initial_baseline
            self.at_site_scan(q, force=self.initial_force)
        # Keep all anchors available; real coverage masks prevent redundant work.
        while True:
            self.iterations += 1
            self.robot.check_budget()
            if self.iterations > 180:
                raise RuntimeError('Joint planner iteration cap')
            pending = [t for c,t in self.tracks.items() if c not in self.robot.cleared]
            if not pending and (len(self.robot.cleared) == 16 or not self.unknown()):
                self.stop_reason = 'cleared_upper_bound_16' if len(self.robot.cleared)==16 else 'continuous_coverage_certificate'
                self.robot.record(dict(kind='completion_certificate', **self.certificate()))
                return self.stop_reason
            if self.family=='adaptive':
                gain=self.scan_gain;self.scan_gain=2.
                self.at_site_scan(self.robot.position)
                self.scan_gain=gain
            else:self.at_site_scan(self.robot.position)
            nodes = self.candidates()
            if not nodes:
                continue
            order = open_route(self.robot.position, [n[2] for n in nodes],restarts=self.route_restarts) if self.route_on else sorted(range(len(nodes)),key=lambda i: math.dist(nodes[i][2],self.robot.position))
            kind, c, point = nodes[order[0]]
            if kind == 'scan':
                self.at_site_scan(point, force=True)
            else:
                track = self.tracks[c]
                self.solve_track(track)
                if self.family=='adaptive' and c in self.cover_targets and len(self.robot.cleared)<16:
                    self.at_site_scan(self.robot.position,force=True)


class SweepPlanner(JointPlanner):
    """Finish targets near the next coverage leg; defer distant returns."""
    def __init__(self, robot, **kwargs):
        super().__init__(robot, family='anchors', **kwargs)

    def candidates(self):
        nodes = super().candidates()
        scans = [n for n in nodes if n[0]=='scan']
        if not scans:
            return nodes
        route = open_route(self.robot.position,[n[2] for n in scans])
        next_scan = scans[route[0]]
        p,q = np.asarray(self.robot.position),next_scan[2]
        targets=[]
        for n in nodes:
            if n[0]!='target':continue
            detour = np.linalg.norm(n[2]-p)+np.linalg.norm(n[2]-q)-np.linalg.norm(q-p)
            if detour <= 350:
                targets.append(n)
        return targets + [next_scan]


class SectorPlanner(JointPlanner):
    """One angular sweep, local open routes with the next station as endpoint."""
    def __init__(self,robot,*,sector_rotation=0.,sector_width=60.,preclear=False,**kwargs):
        super().__init__(robot,**kwargs)
        self.sector_rotation=math.radians(sector_rotation)
        self.sector_width=sector_width
        self.preclear=preclear

    def run(self):
        self.at_site_scan((0.,0.),force=True)
        radius=math.hypot(*self.anchors[1])
        sites=[radius*np.array([math.cos(self.sector_rotation+i*math.pi/3),
                               math.sin(self.sector_rotation+i*math.pi/3)]) for i in range(6)]
        for sector,site in enumerate(sites):
            if not self.unknown():break
            if self.preclear:
                for _ in range(16):
                    p=np.asarray(self.robot.position)
                    good=[t for c,t in self.tracks.items() if c not in self.robot.cleared and
                          np.linalg.norm(t.center-p)+np.linalg.norm(t.center-site)-np.linalg.norm(site-p)<=100]
                    if not good:break
                    self.solve_track(min(good,key=lambda t:np.linalg.norm(t.center-p)))
            self.at_site_scan(site,force=True)
            while True:
                self.robot.check_budget()
                pending=[]
                for c,t in self.tracks.items():
                    if c in self.robot.cleared:continue
                    angle=(math.degrees(math.atan2(t.center[1],t.center[0])-self.sector_rotation)+30)%360
                    if angle <= (sector+1)*60 or sector==5:
                        pending.append(t)
                if not pending:break
                end=sites[sector+1] if sector<5 and self.unknown() else None
                route=open_route(self.robot.position,[t.center for t in pending],end=end)
                self.solve_track(pending[route[0]])
                # Only measurements of uncertain known targets, no blind scans.
                gain=self.scan_gain;self.scan_gain=2.
                self.at_site_scan(self.robot.position)
                self.scan_gain=gain
        while True:
            pending=[t for c,t in self.tracks.items() if c not in self.robot.cleared]
            if not pending:break
            route=open_route(self.robot.position,[t.center for t in pending])
            self.solve_track(pending[route[0]])
        if self.unknown():
            raise RuntimeError('Sector sweep did not certify full coverage')
        self.stop_reason='cleared_upper_bound_16' if len(self.robot.cleared)==16 else 'continuous_coverage_certificate'
        self.robot.record(dict(kind='completion_certificate',**self.certificate()))
        return self.stop_reason
