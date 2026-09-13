"""Literature-inspired sequential cautious baseline; NOT an exact reproduction.

Vander Hook et al. (2014), Algorithm 1: principal-axis normal, shrinking
stand-off, nearer of two locations. Uniform polygon moments replace EKF;
bounded-region certificates replace probabilistic convergence claims.
No simulator truth is accessed. Frozen before official practice evaluation.
"""
import json
import math
from pathlib import Path
from statistics import NormalDist
import numpy as np
from legacy_strategy import Planner as BasePlanner, CLEAR_RADIUS

VERSION = 'q3-literature-cautious-adaptation-20260913'
POLICIES = json.loads(Path(__file__).with_name('policies.json').read_text())

def polygon_moments(poly):
    # Exact area moments of a uniform convex polygon; numerical translation.
    origin = np.mean(poly, axis=0)
    p = poly-origin; q = np.roll(p,-1,axis=0)
    cross = p[:,0]*q[:,1]-q[:,0]*p[:,1]
    area = cross.sum()/2
    if abs(area)<1e-10:
        return origin, (p.T@p)/max(1,len(p))
    mean = ((p+q)*cross[:,None]).sum(axis=0)/(6*area)
    xx = ((p[:,0]**2+p[:,0]*q[:,0]+q[:,0]**2)*cross).sum()/(12*area)
    yy = ((p[:,1]**2+p[:,1]*q[:,1]+q[:,1]**2)*cross).sum()/(12*area)
    xy = ((2*p[:,0]*p[:,1]+p[:,0]*q[:,1]+q[:,0]*p[:,1]+2*q[:,0]*q[:,1])*cross).sum()/(24*area)
    return origin+mean, np.array([[xx,xy],[xy,yy]])-np.outer(mean,mean)

class CautiousPlanner(BasePlanner):
    def __init__(self, robot, beta=.1, scan_radius_m=1200, **kwargs):
        super().__init__(robot)
        self.anchors = [(0.,0.)]+[(scan_radius_m*math.cos(i*math.pi/3),scan_radius_m*math.sin(i*math.pi/3)) for i in range(6)]
        self.beta=beta
        self.max_observations=kwargs.get('max_observations_per_target',40)

    def cautious_point(self, track):
        center,cov=polygon_moments(track.poly)
        values,vectors=np.linalg.eigh(cov)
        axis=vectors[:,-1]; normal=np.array([-axis[1],axis[0]])
        sigma_beta=math.pi/(2*NormalDist().inv_cdf(1-self.beta/2))
        radius=math.sqrt(max(0.,values[-1]))/math.sqrt(sigma_beta**2-math.radians(1)**2/3)
        candidates=[]
        for sign in [-1,1]:
            # Range-limited adaptation: largest stand-off up to the proposed
            # value for which every possible source remains within 999.9 m.
            lo,hi=0.,radius
            if np.max(np.linalg.norm(track.poly-center,axis=1))>999.9: continue
            for _ in range(40):
                mid=(lo+hi)/2; point=center+sign*mid*normal
                if np.max(np.linalg.norm(track.poly-point,axis=1))<=999.9: lo=mid
                else: hi=mid
            point=center+sign*lo*normal
            if all(math.dist(point,h['position'])>=.1 for h in track.history):
                candidates.append(point)
        if not candidates: return track.next_point(np.asarray(self.robot.position))
        point=min(candidates,key=lambda q:math.dist(q,self.robot.position))
        self.robot.record(dict(kind='cautious_choice',channel=track.channel,
            point=point.tolist(),moment_center=center.tolist(),proposed_standoff_m=radius,
            actual_standoff_m=float(np.linalg.norm(point-center)),region_radius_m=track.radius))
        return point

    def solve_track(self, track):
        for _ in range(self.max_observations):
            self.robot.check_budget()
            point=track.safe_clear_point(self.robot.position)
            if point is not None:
                self.robot.record(dict(kind='clear_certificate',channel=track.channel,
                    point=point.tolist(),worst_distance_m=float(np.max(np.linalg.norm(track.poly-point,axis=1)))))
                if not self.robot.clear(tuple(point),track.channel):
                    raise ArithmeticError('Bounded-region clear certificate failed')
                return
            result=self.observe(self.cautious_point(track),track.channel)
            if result['measure_result']=='no_signal':
                raise ArithmeticError('Reception certificate failed')
        raise RuntimeError('Cautious localization observation budget exhausted')

def Planner(robot, *, policy='literature_cautious'):
    return CautiousPlanner(robot,**POLICIES[policy])
