"""Exact heading/radius prior mass at each position, area quadrature of P.

Used only for route ranking. Uniform area/R/heading and a half-type mixture
are modeling assumptions, not official generator facts or hard certificates.
"""
import math
import numpy as np
from scipy.stats import qmc
from shapely.geometry import Point
TAU=2*math.pi

def intersect_arc(intervals,angle):
    lo=(angle-math.pi/2)%TAU;hi=lo+math.pi
    pieces=[(lo,min(hi,TAU))]+([(0.,hi-TAU)] if hi>TAU else [])
    return [(max(a,c),min(b,d)) for a,b in intervals for c,d in pieces if min(b,d)>max(a,c)]

def prior_mass(x,history):
    positive=[h for h in history if h['measure_result']!='no_signal']
    negative=[h for h in history if h['measure_result']=='no_signal']
    angles=[(0.,TAU)];lo=1000.
    for h in positive:
        d=np.asarray(h['point'])-x;distance=float(np.linalg.norm(d));lo=max(lo,distance)
        if h['measure_result']=='near' and distance>5.000001:return 0.
        if h['measure_result']=='direction' and distance<4.999999:return 0.
        if distance>1e-8:angles=intersect_arc(angles,math.atan2(d[1],d[0]))
    if lo>=1500:return 0.
    negatives=[]
    for h in negative:
        d=np.asarray(h['point'])-x;distance=float(np.linalg.norm(d))
        if distance<1e-8:return 0.
        negatives.append((distance,math.atan2(d[1],d[0])+math.pi))
    negatives.sort()
    omni=max(0,min(1500.,negatives[0][0] if negatives else 1500.)-lo)/500.
    current=lo;mass=0.
    for radius,back_angle in negatives:
        stop=min(radius,1500.)
        if stop>current:mass+=(stop-current)*sum(b-a for a,b in angles)/TAU;current=stop
        if radius>=1500:break
        angles=intersect_arc(angles,back_angle)
        if not angles:break
    if angles and current<1500:mass+=(1500-current)*sum(b-a for a,b in angles)/TAU
    return .5*omni+.5*mass/500.

def position_cloud(track,power=7):
    poly=track.poly;c=np.asarray(track.region.convex_hull.centroid.coords[0]);a=poly;b=np.roll(poly,-1,axis=0)
    area=np.abs((a[:,0]-c[0])*(b[:,1]-c[1])-(a[:,1]-c[1])*(b[:,0]-c[0]))/2
    if area.sum()<1e-10:return np.array([track.center]),np.ones(1)
    distribution=np.cumsum(area/area.sum());z=qmc.Sobol(3,scramble=False).random_base2(power)
    idx=np.minimum(np.searchsorted(distribution,z[:,0],side='right'),len(poly)-1);f=np.sqrt(z[:,1])
    pts=(1-f[:,None])*c+f[:,None]*((1-z[:,2,None])*a[idx]+z[:,2,None]*b[idx])
    pts=np.array([p for p in pts if np.linalg.norm(p)<=1800+1e-8 and track.region.covers(Point(*p))])
    if not len(pts):return np.array([track.center]),np.ones(1)
    weights=np.array([prior_mass(x,track.history) for x in pts]);keep=weights>0
    if not keep.any():return np.array([track.region.centroid.coords[0]]),np.ones(1)
    pts=pts[keep];weights=weights[keep];weights/=weights.sum();return pts,weights

def median(points,weights):
    x=weights@points
    for _ in range(100):
        d=np.maximum(np.linalg.norm(points-x,axis=1),1e-7);w=weights/d;y=(w@points)/w.sum()
        if np.linalg.norm(y-x)<1e-5:return y
        x=y
    return x
