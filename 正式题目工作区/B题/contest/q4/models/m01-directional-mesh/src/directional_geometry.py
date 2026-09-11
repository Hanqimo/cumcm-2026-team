"""P4 geometry. Negative radio readings never delete a 1000 m position disk."""
import math
import numpy as np
from bearing_geometry import (outer_disk, disk_halfplanes, wedge, clip_halfplanes,
                              enclosing_circle, diameter)
from clearance_geometry import nearest_clear_point

EPS = 1.0051
CLEAR = 19.5


def triangle_distance_origin(t):
    e = np.roll(t, -1, axis=0) - t
    cross = e[:, 0] * (-t[:, 1]) - e[:, 1] * (-t[:, 0])
    if np.all(cross >= -1e-8) or np.all(cross <= 1e-8):
        return 0.
    u = np.clip(np.sum(-t * e, axis=1) / np.sum(e * e, axis=1), 0, 1)
    return float(np.min(np.linalg.norm(t + u[:, None] * e, axis=1)))


class DirectionalMesh:
    """Every retained equilateral triangle has diameter < minimum radio range.

    For x in a triangle and ANY unit n, one vertex satisfies n.(s-x)>=0.
    Three actual negative readings at its vertices therefore exclude the entire
    triangle for both source types. Closed radiation boundaries are essential.
    """
    def __init__(self, spacing=990.):
        if not 100 <= spacing <= 999:
            raise ValueError('mesh spacing must be in [100,999] metres')
        self.spacing = float(spacing)
        basis = np.array([[spacing, 0.], [spacing / 2, spacing * math.sqrt(3) / 2]])
        k = math.ceil(3600 / spacing) + 2
        triangles = []
        for i in range(-k, k):
            for j in range(-k, k):
                for ids in [((i,j),(i+1,j),(i,j+1)), ((i+1,j+1),(i,j+1),(i+1,j))]:
                    if triangle_distance_origin(np.asarray(ids) @ basis) <= 1800.01:
                        triangles.append(ids)
        keys = sorted(set(v for t in triangles for v in t))
        lookup = {v:i for i,v in enumerate(keys)}
        self.points = np.asarray(keys) @ basis
        self.triangles = np.asarray([[lookup[v] for v in t] for t in triangles], int)
        self.negative = np.zeros((21, len(keys)), bool)

    def add_negative(self, channel, point):
        d = np.linalg.norm(self.points - point, axis=1)
        i = int(np.argmin(d))
        # Only fixed mesh coordinates enter the certificate; nearby is not equal.
        if np.array_equal(np.asarray(point,float),self.points[i]):
            self.negative[channel, i] = True

    def absent(self, channel):
        return bool(np.all(self.negative[channel, self.triangles]))

    def needed(self, channels):
        if not channels:
            return []
        return np.flatnonzero(np.any(~self.negative[channels], axis=0)).tolist()


class DirectionalTrack:
    def __init__(self, channel):
        self.channel = channel
        self.poly = outer_disk((0,0), 1800, 180)
        self.history = []
        self.positive = []
        self.center = None
        self.radius = float('inf')
        self.losses = 0

    def update(self, point, result):
        h = dict(position=np.asarray(point, float).tolist(), **result)
        self.history.append(h)
        if result['measure_result'] == 'no_signal':
            self.losses += 1
            return
        self.losses = 0
        p = self.poly
        if result['measure_result'] == 'direction':
            p = clip_halfplanes(p, *wedge(point, result['svd_deg'], EPS))
        elif result['measure_result'] != 'near':
            raise ValueError('Unknown radio result')
        r = 5.000001 if result['measure_result'] == 'near' else 1500.000001
        p = clip_halfplanes(p, *disk_halfplanes(point, r, 180))
        if not len(p):
            raise ArithmeticError('Empty bounded-bearing region; inspect observations')
        self.poly = p
        self.center, self.radius, _ = enclosing_circle(p)
        self.positive.append(h)

    def safe_point(self, position):
        if self.radius > CLEAR:
            return None
        return nearest_clear_point(self.poly, position, CLEAR, self.center)

    def optical_cover(self, spacing=26.):
        """Cover the entire conservative polygon by rotated square cells.

        Querying each intersecting cell centre succeeds at least once, because
        every point in a 26 m square is <=18.385 m from its centre. Failed optical
        attempts are expected, paid, and never confused with certified attempts.
        """
        _, (i,j) = diameter(self.poly)
        axis = self.poly[j] - self.poly[i]
        axis = axis / max(np.linalg.norm(axis), 1e-12)
        if np.linalg.norm(axis) < .5:
            return [self.center.copy()]
        basis = np.array([axis, [-axis[1], axis[0]]])
        p = self.poly @ basis.T
        lo = np.floor((p.min(axis=0)-1e-7) / spacing).astype(int)
        hi = np.floor((p.max(axis=0)+1e-7) / spacing).astype(int)
        cells = []
        A = np.array([[1.,0.],[-1.,0.],[0.,1.],[0.,-1.]])
        for a in range(lo[0], hi[0]+1):
            for b in range(lo[1], hi[1]+1):
                x,y = a*spacing,b*spacing
                if len(clip_halfplanes(p, A, np.array([x+spacing,-x,y+spacing,-y]))):
                    cells.append((np.array([x,y])+spacing/2) @ basis)
        return cells

    def hypotheses(self):
        """Finite planning hypotheses, NOT a posterior or completeness proof.

        Retain both omnidirectional and directional possibilities; all negative
        observations use the range-OR-backside condition. Empty sample support
        does not imply an empty continuous feasible state.
        """
        p = self.poly
        middle = p.mean(axis=0)
        ids = np.linspace(0,len(p)-1,min(12,len(p))).astype(int)
        positions = np.vstack([middle, p[ids], .5*p[ids]+.5*middle,
                               .8*p[ids]+.2*middle])
        angles = np.arange(72) * math.pi/36
        normals = np.column_stack([np.cos(angles), np.sin(angles)])
        states = []
        for g in positions:
            lower = max([1000.] + [math.dist(g,h['position']) for h in self.positive])
            if lower > 1500.00001:
                continue
            for r in np.unique([min(1500.,lower+1e-5),(lower+1500.)/2,1500.]):
                valid = np.ones(72, bool)
                omni = True
                for h in self.history:
                    v = np.asarray(h['position']) - g
                    within = np.linalg.norm(v) <= r+1e-7
                    if h['measure_result'] == 'no_signal':
                        valid &= (~within) | (normals @ v < -1e-7)
                        omni &= not within
                    else:
                        valid &= within & (normals @ v >= -1e-7)
                        omni &= bool(within)
                for n in normals[valid]:
                    states.append([*g,r,*n,0.])
                if omni:
                    states.append([*g,r,0.,0.,1.])
        return np.asarray(states, float).reshape(-1,6)

    def next_point(self, position, visibility=True):
        c,r = self.center,self.radius
        _,(i,j) = diameter(self.poly)
        axis = self.poly[j]-self.poly[i]
        axis /= max(np.linalg.norm(axis),1e-12)
        normal = np.array([-axis[1],axis[0]])
        last = np.asarray(self.positive[-1]['position'])
        offset = max(30.,min(180.,.3*r))
        candidates = [c,c+normal*offset,c-normal*offset]
        for t in [.45,.75]:
            for side in [-1,0,1]:
                candidates.append(last+t*(c-last)+side*normal*offset)
        for h in self.positive[-3:]:
            candidates += [(last+np.asarray(h['position']))/2]
        candidates = [q for q in candidates if all(math.dist(q,h['position']) >= 8
                                                   for h in self.history)]
        if not candidates:
            return None, dict(reason='no_distinct_measurement')
        if not visibility:
            q = min(candidates[:3],key=lambda q:math.dist(q,position))
            return q, dict(method='nearest_geometry',visibility_guaranteed=False)
        states = self.hypotheses()
        scores = []
        for q in candidates:
            if len(states):
                delta = q-states[:,:2]
                heard = (np.linalg.norm(delta,axis=1)<=states[:,2]) & (
                    (np.sum(delta*states[:,3:5],axis=1)>=0) | (states[:,5]>0))
                pv = float(np.mean(heard))
            else:
                pv = .5
            # Three readings estimate information value only; no minimax claim.
            angle = math.degrees(math.atan2(c[1]-q[1],c[0]-q[0]))
            radii = []
            for e in [-1.,0.,1.]:
                poly = clip_halfplanes(self.poly,*wedge(q,angle+e,EPS))
                radii.append(enclosing_circle(poly)[1] if len(poly) else r)
            after = float(np.mean(radii))
            score = math.dist(position,q)/5+6 + pv*(math.dist(q,c)/5+2*after/5) + (
                1-pv)*(math.dist(q,last)/5+2*r/5+20)
            scores.append((score,q,pv,after))
        score,q,pv,after = min(scores,key=lambda v:v[0])
        return q,dict(method='sample_visibility_cost',hypotheses=len(states),
                      visibility_fraction=pv,predicted_radius_m=after,score_s=score,
                      visibility_guaranteed=False)
