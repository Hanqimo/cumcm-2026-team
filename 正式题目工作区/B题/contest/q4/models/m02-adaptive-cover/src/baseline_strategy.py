"""P4 initial strategy: directional discovery certificate + bounded localization."""
import json
import math
from pathlib import Path
import numpy as np
from directional_geometry import DirectionalMesh, DirectionalTrack, CLEAR

VERSION = 'p4-directional-mesh-v1.1-research'
POLICIES = json.loads((Path(__file__).parent/'policies.json').read_text(encoding='utf-8'))


def open_route(position, points):
    """Fixed-start, free-end nearest-neighbour path followed by bounded 2-opt."""
    if not len(points):
        return []
    p = np.vstack([position,points])
    d = np.linalg.norm(p[:,None]-p[None,:],axis=2)
    left = set(range(1,len(p))); route = [0]
    while left:
        j = min(left,key=lambda j:(d[route[-1],j],j))
        route.append(j); left.remove(j)
    for _ in range(30):
        best = None; gain = 1e-7
        for i in range(1,len(route)-1):
            for j in range(i+1,len(route)):
                old,new = d[route[i-1],route[i]],d[route[i-1],route[j]]
                if j+1<len(route):
                    old+=d[route[j],route[j+1]];new+=d[route[i],route[j+1]]
                if old-new>gain:
                    gain,best=old-new,(i,j)
        if best is None:
            break
        i,j=best;route[i:j+1]=reversed(route[i:j+1])
    return [i-1 for i in route[1:]]


class Planner:
    def __init__(self, robot, policy='directional_v1'):
        self.robot = robot
        self.parameters = POLICIES[policy]
        self.mesh = DirectionalMesh(self.parameters['mesh_spacing_m'])
        self.tracks = {}
        self.observations = {c:[] for c in range(1,21)}
        self.stop_reason = None
        self.optical_fallbacks = 0
        self.radio_losses = 0

    def unknown(self):
        if len(self.robot.discovered)>=16:
            # The upper bound applies to distinct discovered channels as well
            # as cleared channels; finish these targets without further search.
            return []
        return [c for c in range(1,21) if c not in self.robot.discovered and not self.mesh.absent(c)]

    def observe(self, point, channel):
        result = self.robot.measure(tuple(map(float,point)),channel)
        self.observations[channel].append((np.asarray(point).copy(),result))
        if result['measure_result']=='no_signal':
            self.mesh.add_negative(channel,point)
            if channel in self.tracks:
                self.radio_losses += 1
        elif channel not in self.tracks:
            self.tracks[channel] = DirectionalTrack(channel)
            for q,r in self.observations[channel][:-1]:
                self.tracks[channel].update(q,r)
        if channel in self.tracks:
            t = self.tracks[channel];t.update(point,result)
            if result['measure_result']!='no_signal':
                self.robot.record(dict(kind='region',channel=channel,vertices=t.poly.tolist(),
                                       center=t.center.tolist(),radius_m=t.radius))
        return result

    def scan(self, index):
        point = self.mesh.points[index]
        channels = [c for c in self.unknown() if not self.mesh.negative[c,index]]
        if channels:
            self.robot.scanned_sites += 1
        for c in sorted(channels,key=lambda c:(c!=self.robot.channel,c)):
            self.robot.check_budget()
            result = self.observe(point,c)
            if result['measure_result']=='near':
                self.certified_clear(self.tracks[c])
        # Known-channel opportunistic measurements are deliberately not automatic.

    def certified_clear(self, track):
        q = track.safe_point(self.robot.position)
        if q is None:
            return False
        bound = float(np.max(np.linalg.norm(track.poly-q,axis=1)))
        if bound>CLEAR+1e-6:
            raise ArithmeticError('Unsafe proposed clear')
        self.robot.record(dict(kind='clear_certificate',channel=track.channel,
                               point=q.tolist(),worst_distance_m=bound))
        if not self.robot.clear(tuple(map(float,q)),track.channel):
            raise ArithmeticError('Certified optical clear failed; inspect model and logs')
        return True

    def fallback(self, track):
        self.optical_fallbacks += 1
        cells = track.optical_cover()
        self.robot.record(dict(kind='optical_cover',channel=track.channel,spacing_m=26.,
                               cell_radius_m=13*math.sqrt(2),vertices=track.poly.tolist(),
                               points=[p.tolist() for p in cells]))
        if len(cells)>5000:
            raise RuntimeError('Unexpected optical cover size; inspect geometry')
        # A complete finite cover remains available even if radio planning fails.
        while cells:
            self.robot.check_budget()
            i = min(range(len(cells)),key=lambda i:math.dist(cells[i],self.robot.position))
            q = cells.pop(i)
            self.robot.record(dict(kind='optical_attempt',channel=track.channel,point=q.tolist()))
            if self.robot.clear(tuple(map(float,q)),track.channel):
                return
        raise ArithmeticError('All optical-cover points failed; physical/geometry contradiction')

    def solve_track(self, track):
        for _ in range(self.parameters['max_local_measurements']):
            self.robot.check_budget()
            if self.certified_clear(track):
                return
            if track.losses>=self.parameters['max_consecutive_losses']:
                break
            q,info = track.next_point(self.robot.position,self.parameters['visibility_planning'])
            if q is None:
                break
            self.robot.record(dict(kind='measurement_plan',channel=track.channel,point=q.tolist(),**info))
            self.observe(q,track.channel)
        if not self.certified_clear(track):
            self.fallback(track)

    def run(self):
        origin = int(np.argmin(np.linalg.norm(self.mesh.points,axis=1)))
        self.scan(origin)
        for _ in range(1000):
            self.robot.check_budget()
            if len(self.robot.cleared)>=16:
                self.stop_reason='cleared_upper_bound_16';return
            active = [c for c in self.tracks if c not in self.robot.cleared]
            unknown = self.unknown()
            if not active and not unknown:
                self.stop_reason='all_known_cleared_and_all_other_channels_mesh_excluded';return
            sites = self.mesh.needed(unknown)
            if active and not self.parameters['joint_routing']:
                c = min(active,key=lambda c:math.dist(self.robot.position,self.tracks[c].center))
                self.solve_track(self.tracks[c]);continue
            nodes = [('scan',i,self.mesh.points[i]) for i in sites]
            nodes += [('target',c,self.tracks[c].center) for c in active]
            if not nodes:
                raise RuntimeError('No available action without completion certificate')
            order = open_route(self.robot.position,[n[2] for n in nodes])
            kind,index,_ = nodes[order[0]]
            if kind=='scan':
                self.scan(index)
            else:
                self.solve_track(self.tracks[index])
        raise RuntimeError('Main action iteration bound reached without certificate')

    def certificate(self):
        absent = [c for c in range(1,21) if c not in self.robot.discovered and self.mesh.absent(c)]
        return dict(problem=4,reason=self.stop_reason,complete=bool(self.stop_reason),
                    cleared_channels=sorted(self.robot.cleared),excluded_channels=absent,
                    observed_but_uncleared=sorted(self.robot.discovered-self.robot.cleared),
                    mesh_spacing_m=self.mesh.spacing,mesh_points=self.mesh.points.tolist(),
                    triangles=self.mesh.triangles.tolist(),
                    negative_vertex_indices={str(c):np.flatnonzero(self.mesh.negative[c]).tolist() for c in absent},
                    optical_fallbacks=self.optical_fallbacks,known_channel_radio_losses=self.radio_losses,
                    assumptions='Static sources; closed 180-degree half-plane or omnidirectional; R>=1000')
