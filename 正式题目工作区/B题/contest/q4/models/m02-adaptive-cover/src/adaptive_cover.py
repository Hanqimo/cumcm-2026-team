"""Cell-wise directional certificates from arbitrary measured station triples.

A cell Q is excluded by three negative sites a,b,c if Q lies in their triangle
and every vertex of Q lies within 999.99 m of all three sites. Convexity extends
both conditions to the whole cell, including the continuous arena boundary.
"""
import itertools,math,json
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
from directional_geometry import DirectionalMesh
from bearing_geometry import outer_disk


def split_triangle(t,depth):
    if not depth:return [t]
    a,b,c=t;ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
    return sum([split_triangle(np.array(x),depth-1) for x in
                [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]],[])


class AdaptiveMesh(DirectionalMesh):
    def __init__(self,spacing=990.,depth=2,layout=None):
        super().__init__(spacing)
        arena=Polygon(outer_disk((0.,0.),1800.,360))
        cells=[]
        for ids in self.triangles:
            for t in split_triangle(self.points[ids],depth):
                cell=Polygon(t).intersection(arena)
                if not cell.is_empty and cell.area>1e-9:
                    cells.append(np.asarray(cell.exterior.coords[:-1]))
        if layout:
            data=json.loads((Path(__file__).parent/layout).read_text())
            self.points=np.asarray(data['points']);self.negative=np.zeros((21,len(self.points)),bool)
            self.triangles=np.empty((0,3),int)
            cells=[np.asarray(c) for c in data['cells']]
        self.cells=cells
        width=max(map(len,cells));v=np.empty((len(cells),width,2))
        for i,c in enumerate(cells):v[i]=c[0];v[i,:len(c)]=c
        self.vertices=v;self.corner_width=width;self.full=(1<<(len(cells)*width))-1
        self.witnesses=[];self.point_masks=[];self.position=np.zeros(2)
        self.cache={};self.last_needed=None
        for q in self.points:self.point_masks.append(self.range_mask(q))
        for ids in itertools.combinations(range(len(self.points)),3):self.add_witness(ids)
        if self.cover_bits(range(len(self.points)))!=self.full:
            raise ArithmeticError('Adaptive witness library does not cover arena cells')

    def range_mask(self,q):
        return np.max(np.sum((self.vertices-q)**2,axis=2),axis=1)<=999.99**2

    def add_witness(self,ids):
        mask=self.point_masks[ids[0]]&self.point_masks[ids[1]]&self.point_masks[ids[2]]
        if not np.any(mask):return
        t=self.points[list(ids)];e=np.roll(t,-1,axis=0)-t
        area=np.cross(t[1]-t[0],t[2]-t[0])
        if abs(area)<1e-6:return
        selected=np.flatnonzero(mask);v=self.vertices[selected]
        corners=np.repeat(mask[:,None],self.corner_width,axis=1)
        for a,d in zip(t,e):
            delta=v-a;cross=d[0]*delta[:,:,1]-d[1]*delta[:,:,0]
            # Small positive physical margin is unnecessary on shared edges;
            # tolerance is <=1e-8 m when scaled by edge length.
            corners[selected]&=cross*np.sign(area)>=-1e-8*np.linalg.norm(d)
        if np.any(corners):
            bits=int.from_bytes(np.packbits(corners.ravel(),bitorder='little').tobytes(),'little')
            self.witnesses.append((sum(1<<i for i in ids),bits,tuple(ids)))

    def cover_bits(self,indices):
        selected=sum(1<<int(i) for i in indices)
        if selected in self.cache:return self.cache[selected]
        bits=0
        for needed,mask,_ in self.witnesses:
            if selected&needed==needed:bits|=mask
        self.cache[selected]=bits
        return bits

    def add_point(self,q):
        d=np.linalg.norm(self.points-q,axis=1);nearest=int(np.argmin(d))
        if d[nearest]<1e-6:return nearest
        index=len(self.points);self.points=np.vstack([self.points,q])
        self.negative=np.pad(self.negative,((0,0),(0,1)))
        self.point_masks.append(self.range_mask(q))
        for i,j in itertools.combinations(range(index),2):self.add_witness((i,j,index))
        self.cache={};return index

    def add_negative(self,channel,point):
        index=self.add_point(np.asarray(point))
        self.negative[channel,index]=True

    def absent(self,channel):
        return self.cover_bits(np.flatnonzero(self.negative[channel]))==self.full

    def needed(self,channels):
        if not channels:return []
        actual=set(np.flatnonzero(np.all(self.negative[channels],axis=0)).tolist())
        future=set(range(len(self.points)))-actual
        # Only original guaranteed fallback sites are scheduled by default.
        # Extra actual observations can remove those future obligations.
        order=sorted(future,key=lambda i:np.linalg.norm(self.points[i]-self.position),reverse=True)
        for i in order:
            candidate=actual|(future-{i})
            if self.cover_bits(candidate)==self.full:future.remove(i)
        self.last_needed=sorted(future)
        return self.last_needed

    def cell_certificate(self,channel):
        selected=sum(1<<int(i) for i in np.flatnonzero(self.negative[channel]))
        covered=0;proof=[]
        for needed,mask,ids in self.witnesses:
            new=mask&~covered
            if selected&needed==needed and new:
                proof.append(dict(stations=list(ids),corner_indices=[i for i in range(len(self.cells)*self.corner_width) if new>>i&1]))
                covered|=mask
        return dict(complete=covered==self.full,corner_width=self.corner_width,witnesses=proof)
