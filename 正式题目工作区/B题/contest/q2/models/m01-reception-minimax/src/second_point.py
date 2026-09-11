"""Q2 M01 v01: guaranteed-reception candidate region + minimax disk radius.

The spatial search is finite; no claim of continuous global optimality is made.
Reading bins are OUTER enclosures, not samples advertised as worst-case bounds.
"""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'contest/q1/models/m01-bounded-bearing/src'))
from bearing_geometry import (unit,wedge,outer_disk,disk_halfplanes,clip_halfplanes,
    enclosing_circle,diameter,bearing,angle_difference)


def to_global(local,sensor,theta):
    u=unit(theta);v=np.array([-u[1],u[0]])
    return np.asarray(sensor)+local[0]*u+local[1]*v


def to_local(point,sensor,theta):
    d=np.asarray(point)-np.asarray(sensor);u=unit(theta);v=np.array([-u[1],u[0]])
    return np.array([d@u,d@v])


def candidate_margins(local,epsilon_deg=1.,rmin=1000.,budget=1000.,lateral_min=20.):
    """All margins >= 0 means the point belongs to C(B,h).

    Circle margin uses the smaller of the two endpoint-disk margins.
    """
    a,b=np.asarray(local,float);e=np.deg2rad(epsilon_deg)
    centers=[rmin*unit(-epsilon_deg),rmin*unit(epsilon_deg)]
    return {'travel_m':budget-np.hypot(a,b),'origin_disk_m':rmin-np.hypot(a,b),
      'endpoint_disks_m':min(rmin-np.linalg.norm(np.array([a,b])-p) for p in centers),
      'lateral_separation_m':abs(b)*np.cos(e)-a*np.sin(e)-lateral_min}


def in_candidate(local,**kwargs):
    return min(candidate_margins(local,**kwargs).values())>=-1e-8


def first_region(sensor=(0.,0.),theta=0.,epsilon_deg=1.,rmax=1500.,arena_radius=1800.,sides=360):
    """Convex outer prior; omits the 5 m inner hole conservatively."""
    poly=outer_disk(sensor,rmax,sides)
    poly=clip_halfplanes(poly,*wedge(sensor,theta,epsilon_deg))
    if arena_radius is not None:
        poly=clip_halfplanes(poly,*disk_halfplanes([0,0],arena_radius,sides))
    if len(poly)<3:
        raise ValueError('Initial observation has empty/degenerate prior; inspect input')
    return poly


def posterior(poly,point,reading_deg,epsilon_deg=1.):
    return clip_halfplanes(poly,*wedge(point,reading_deg,epsilon_deg))


def angular_interval(poly,point):
    # If point lies in/on the polygon, use all directions (baseline comparison).
    edges=np.roll(poly,-1,axis=0)-poly;rel=np.asarray(point)-poly
    crosses=edges[:,0]*rel[:,1]-edges[:,1]*rel[:,0]
    if np.all(crosses>=-1e-8) or np.all(crosses<=1e-8):
        return 0.,360.
    ref=bearing(poly.mean(axis=0),point)
    angles=np.array([ref+float(angle_difference(bearing(p,point),ref)) for p in poly])
    if np.ptp(angles)>180+1e-7:
        # Safe fallback, not a heuristic truncation across 0/360.
        return 0.,360.
    return float(angles.min()),float(angles.max())


def worst_radius_upper(poly,point,epsilon_deg=1.,bin_width_deg=.5):
    """Upper bound for continuous future reading uncertainty, modulo FP error.

    Every actual reading belongs to a bin. Enlarging its central wedge by half
    the bin width contains the posterior for all readings in the bin.
    """
    if bin_width_deg<=0:raise ValueError('bin width must be positive')
    low,high=angular_interval(poly,point)
    low-=epsilon_deg;high+=epsilon_deg
    edges=np.linspace(low,high,int(np.ceil((high-low)/bin_width_deg))+1)
    worst=-1.;worst_center=None;worst_poly=None
    for left,right in zip(edges[:-1],edges[1:]):
        center=(left+right)/2
        p=posterior(poly,point,center,epsilon_deg+(right-left)/2)
        if not len(p):continue
        _,radius,_=enclosing_circle(p)
        if radius>worst:
            worst=radius;worst_center=center%360;worst_poly=p
    if worst<0:raise ArithmeticError('No nonempty prediction bins')
    return {'radius_upper_m':worst,'worst_bin_center_deg':worst_center,
      'bin_width_deg':float(np.max(np.diff(edges))),'n_bins':len(edges)-1,
      'worst_enclosure':worst_poly.tolist()}


def fixed_point(sensor=(0.,0.),theta=0.,step=500.,alpha_deg=45.):
    return to_global(step*unit(alpha_deg),sensor,theta)


def linearized_radius(r1,r2,intersection_angle_deg,epsilon_deg=1.):
    """Local sensitivity proxy ONLY, not a bounded-error certificate."""
    beta=np.deg2rad(intersection_angle_deg)
    return np.deg2rad(epsilon_deg)*np.sqrt(r1*r1+r2*r2+2*r1*r2*abs(np.cos(beta)))/abs(np.sin(beta))
