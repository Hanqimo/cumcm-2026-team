"""Candidate policy only; all paid physics comes from shared Robot."""
import math,json
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon
from scipy.spatial import ConvexHull
import base
from optimize import Integrated,RING

class Planner(Integrated):
    def __init__(self,robot,policy='control'):
        if policy not in ['control','recovery','optcover','mobile','combined','route','route_opt','greedyopt']:raise ValueError(policy)
        super().__init__(robot,'J500');self.policy=policy;self.relocations=0
        self.leaves=[]
        if policy=='mobile':
            for leaf in RING['proof']:
                lo,hi=leaf['lo'],leaf['hi'];c=np.array([lo,[hi[0],lo[1]],hi,[lo[0],hi[1]]])
                self.leaves.append((c,leaf['stations']))
            self.checked_moves=set()
    def candidates(self,t):
        raw=super().candidates(t)
        if self.policy not in ['recovery','combined'] or t.history[-1]['measure_result']!='no_signal':return raw
        last=np.array(t.positive[-1]['point']);c=t.center
        # Recover from a known positive viewpoint; hypotheses still rank these.
        for f in [.25,.5,.75]:
            q=last+f*(c-last)
            if all(math.dist(q,h['point'])>2 for h in t.history):raw.append(q)
        return raw
    def optical_cover(self,t):
        if self.policy in ['greedyopt','route_opt']:return self.greedy_optical(t)
        if self.policy not in ['optcover','combined']:return super().optical_cover(t)
        self.fallbacks+=1
        poly=t.poly;_,(i,j)=base.diameter(poly);u=poly[j]-poly[i];u=u/max(np.linalg.norm(u),1e-10);v=np.array([-u[1],u[0]]);basis=np.array([u,v])
        rotated=poly@basis.T;lo=rotated.min(axis=0);hi=rotated.max(axis=0);width=hi[1]-lo[1]
        # Every rectangle has circumradius <=19.5m; intersecting cells retained.
        if width<=36:
            height=max(width,1e-6);step=2*math.sqrt(19.5**2-(height/2)**2)
        else:height=27.5;step=27.5
        nx=max(1,math.ceil((hi[0]-lo[0])/step));ny=max(1,math.ceil((hi[1]-lo[1])/height));nodes=[]
        for ix in range(nx):
            for iy in range(ny):
                a=lo+np.array([ix*step,iy*height]);b=np.minimum(hi,a+[step,height]);corners=np.array([a,[b[0],a[1]],b,[a[0],b[1]]])@basis
                if Polygon(corners).intersects(t.region):nodes.append(((a+b)/2@basis,corners))
        self.robot.record(dict(kind='optical_cover_certificate',channel=t.channel,width_m=float(width),cells=[c.tolist() for q,c in nodes],centers=[q.tolist() for q,c in nodes]))
        while nodes:
            k=min(range(len(nodes)),key=lambda k:math.dist(nodes[k][0],self.robot.position));q,c=nodes.pop(k)
            if not Polygon(c).intersects(t.region):continue
            if t.radius<=19.5:
                if not self.try_clear(t,t.center,'enclosing circle certificate'):raise ArithmeticError('certified clear failed')
                return
            if self.try_clear(t,q,'oriented rectangle optical cover'):return
        raise ArithmeticError('exhausted certified optical rectangles')
    def greedy_optical(self,t):
        self.fallbacks+=1;step=25.;xmin,ymin,xmax,ymax=t.region.bounds;nodes=[]
        for ix in range(math.floor(xmin/step),math.floor(xmax/step)+1):
            for iy in range(math.floor(ymin/step),math.floor(ymax/step)+1):
                corners=np.array([[ix*step,iy*step],[(ix+1)*step,iy*step],[(ix+1)*step,(iy+1)*step],[ix*step,(iy+1)*step]])
                if Polygon(corners).intersects(t.region):nodes.append((corners.mean(axis=0),corners))
        self.robot.record(dict(kind='optical_cover_certificate',channel=t.channel,cells=[c.tolist() for q,c in nodes],centers=[q.tolist() for q,c in nodes]))
        while nodes:
            if t.radius<=19.5:
                if not self.try_clear(t,t.center,'enclosing circle certificate'):raise ArithmeticError('certified clear failed')
                return
            candidates=sorted(range(len(nodes)),key=lambda i:math.dist(nodes[i][0],self.robot.position))[:48]
            scores=[]
            for i in candidates:
                q,c=nodes[i];area=t.region.intersection(Point(*q).buffer(19.999,quad_segs=16)).area
                scores.append(area/(3+math.dist(q,self.robot.position)/5))
            k=candidates[int(np.argmax(scores))];q,c=nodes.pop(k)
            if not Polygon(c).intersects(t.region):continue
            if self.try_clear(t,q,'optical area per paid second'):return
        raise ArithmeticError('exhausted optical covering')
    def route(self,remaining):
        route=super().route(remaining)
        if self.policy!='mobile' or not route:return route
        idx=route[0];q=self.robot.position
        key=(idx,round(float(q[0]),3),round(float(q[1]),3))
        if idx==0 or idx>7 or key in self.checked_moves or not 2<math.dist(q,self.sites[idx])<=250:return route
        self.checked_moves.add(key);new=self.sites.copy();new[idx]=q
        for corners,ids in self.leaves:
            if idx not in ids:continue
            pts=new[ids]
            if np.linalg.norm(pts[:,None,:]-corners[None,:,:],axis=2).max()>999.99:return route
            try:h=ConvexHull(pts)
            except Exception:return route
            if (corners@h.equations[:,:2].T+h.equations[:,2]).max()>1e-8:return route
        self.robot.record(dict(kind='relocate',site=idx,old=self.sites[idx].tolist(),new=q.tolist()))
        self.sites=new;self.relocations+=1
        return route
    def run(self):
        reason=self.joint_route_run() if self.policy in ['route','route_opt'] else super().run()
        self.robot.record(dict(kind='final_certificate',reason=reason,sites=self.sites.tolist(),visited=sorted(self.visited),relocations=self.relocations,policy=self.policy))
        return reason
    def joint_order(self,remaining):
        keys=[('site',i) for i in sorted(remaining)]+[('target',ch) for ch in sorted(self.tracks) if ch not in self.robot.cleared]
        pts=[self.sites[k] if kind=='site' else self.tracks[k].center for kind,k in keys]
        if not pts:return []
        pp=np.vstack([self.robot.position,pts]);dm=np.linalg.norm(pp[:,None,:]-pp[None,:,:],axis=2);todo=set(range(1,len(pp)));order=[0]
        while todo:
            k=min(todo,key=lambda k:(dm[order[-1],k],k));order.append(k);todo.remove(k)
        for _ in range(100):
            change=None;best=-1e-7
            for i in range(1,len(order)-1):
                a,b=order[i-1],order[i]
                for j in range(i+1,len(order)):
                    c=order[j];delta=dm[a,c]-dm[a,b]
                    if j+1<len(order):
                        d=order[j+1];delta+=dm[b,d]-dm[c,d]
                    if delta<best:best=delta;change=(i,j)
            if change is None:break
            i,j=change;order[i:j+1]=order[i:j+1][::-1]
        self.robot.record(dict(kind='joint_route',nodes=[dict(kind=keys[k-1][0],id=keys[k-1][1],point=pp[k].tolist()) for k in order[1:]],length_m=float(sum(dm[a,b] for a,b in zip(order[:-1],order[1:])))))
        return [keys[k-1] for k in order[1:]]
    def joint_route_run(self):
        remaining=set(range(len(self.sites)))
        while remaining or any(ch not in self.robot.cleared for ch in self.tracks):
            order=self.joint_order(remaining);kind,k=order[0]
            if kind=='target':self.solve(k)
            else:
                q=self.sites[k];remaining.remove(k)
                channels=[ch for ch in range(1,21) if ch not in self.tracks]
                channels += [ch for ch,t in sorted(self.tracks.items()) if ch not in self.robot.cleared and self.share_worth(t,q)]
                for ch in sorted(channels):
                    if ch in self.tracks:self.shared_measures+=1
                    self.observe(q,ch)
                self.visited.add(k);self.scan_history.append(dict(site=k,point=q.tolist(),channels=sorted(channels)))
                self.robot.record(dict(kind='scan_site',site=k,channels=sorted(channels)))
            if len(self.robot.cleared)==16:return 'count upper bound'
        for ch in range(1,21):
            if ch not in self.tracks:assert len(self.negatives[ch])==len(self.sites)
        return 'mesh certificate and all discovered cleared'
