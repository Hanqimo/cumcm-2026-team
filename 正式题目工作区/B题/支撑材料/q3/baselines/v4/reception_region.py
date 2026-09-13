"""Exact first-positive reception separator on a convex polygon outer region.

For each x, the least admissible reception radius is max(R0, |x-s|).
Evaluate the maximum violation over polygon vertices, edge/circle crossings,
and the antipodal stationary point on the R0-circle when inside the polygon.
"""
import math
import numpy as np


def reception_violation(poly,first_sensor,query,r0=1000.):
    poly=np.asarray(poly,float);s=np.asarray(first_sensor,float);q=np.asarray(query,float)
    if not len(poly):raise ValueError('Empty source region')
    points=list(poly)
    edges=np.roll(poly,-1,axis=0)-poly
    for p,d in zip(poly,edges):
        a=float(np.dot(d,d))
        if a<1e-18:continue
        offset=p-s;b=2*float(np.dot(offset,d));c=float(np.dot(offset,offset)-r0*r0)
        discr=b*b-4*a*c
        if discr>=0:
            root=math.sqrt(discr)
            for t in [(-b-root)/(2*a),(-b+root)/(2*a)]:
                if 0<=t<=1:points.append(p+t*d)
    d=q-s;length=float(np.linalg.norm(d))
    if length>1e-12:
        far=s-r0*d/length
        delta=far-poly
        cross=edges[:,0]*delta[:,1]-edges[:,1]*delta[:,0]
        if np.all(cross>=-1e-8*np.maximum(1.,np.linalg.norm(edges,axis=1))):points.append(far)
    points=np.asarray(points)
    values=np.sum((points-q)**2,axis=1)-np.maximum(r0*r0,np.sum((points-s)**2,axis=1))
    k=int(np.argmax(values))
    return float(values[k]),points[k].copy()
