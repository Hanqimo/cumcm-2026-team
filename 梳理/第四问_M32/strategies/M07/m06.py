"""M06: certified dynamic discovery coverage and service-cost routing."""
import math
import numpy as np
import base
from previous import Planner as Previous
from coverage import Coverage
from optimize import open_route,length

class Planner(Previous):
    def __init__(self,robot,policy='coverage'):
        if policy not in ['baseline','coverage','service','combined','pool','pool_service','count','count_service','area_service']:raise ValueError(policy)
        super().__init__(robot,'route_opt')
        self.new_policy=policy;self.coverage=Coverage() if policy in ['coverage','combined','pool','pool_service'] else None
        self.service=policy in ['service','combined','pool_service','count_service','area_service'];self.first_choice={};self.service_choices={}
        self.next_waypoint=None
        self.replacements=0;self.removed=0

    def select(self,t):
        if t.channel in self.first_choice:return self.first_choice.pop(t.channel)
        return super().select(t)

    def try_clear(self,t,q,reason):
        if self.new_policy=='area_service' and reason=='enclosing circle certificate':
            # Inner disk of the exact clearance region, with 0.5m safety margin.
            p=self.robot.position;c=t.center;r=max(0.,19.5-t.radius)
            d=math.dist(p,c);near=c+(p-c)*min(1.,r/max(d,1e-12))
            options=[c,near]+[c+r*np.array([math.cos(a),math.sin(a)]) for a in np.arange(32)*2*math.pi/32]
            def cost(x):return math.dist(p,x)+(math.dist(x,self.next_waypoint) if self.next_waypoint is not None else 0)
            q=min(options,key=cost)
            assert np.linalg.norm(t.poly-q,axis=1).max()<=19.501
            self.robot.record(dict(kind='service_region_clear',channel=t.channel,center=c.tolist(),radius=t.radius,point=np.asarray(q).tolist(),next=np.asarray(self.next_waypoint).tolist() if self.next_waypoint is not None else None))
        return super().try_clear(t,q,reason)

    def service_options(self,t):
        if t.radius<=19.5:return [(t.center,5.)]
        qs=self.candidates(t)
        if not qs:return [(t.center,5.+t.radius/5)]
        g,rad,n=base.heading_hypotheses(t)
        out=[]
        for q in qs:
            if not len(g):after=t.radius;prob=0.
            else:
                d=q-g;vis=(np.linalg.norm(d,axis=1)<=rad)&((d*n).sum(axis=1)>=-1e-8)
                prob=float(vis.mean());vg=g[vis];sizes=[];weights=[]
                if len(vg):
                    ug,counts=np.unique(np.round(vg,8),axis=0,return_counts=True)
                    for x,count in zip(ug,counts):
                        if math.dist(x,q)<=5:r=5.
                        else:
                            a=math.degrees(math.atan2(x[1]-q[1],x[0]-q[0]))
                            pp=base.clip_halfplanes(t.poly,*base.wedge(q,a,base.EPS))
                            r=base.enclosing_circle(pp)[1] if len(pp) else t.radius
                        sizes.append(r);weights.append(count)
                after=float(np.average(sizes,weights=weights)) if sizes else t.radius
            residual=5.+max(0,math.dist(q,t.center)-19)/5
            residual+=prob*(after/5+8*max(0,math.log(max(after/19,1),2)))
            residual+=(1-prob)*(35+min(t.radius,350)/2.5)
            out.append((q,float(residual)))
        return out

    def joint_order(self,remaining):
        if not self.service:return super().joint_order(remaining)
        keys=[('site',i) for i in sorted(remaining)]+[('target',ch) for ch in sorted(self.tracks) if ch not in self.robot.cleared]
        if not keys:return []
        exits=[self.robot.position]+[self.sites[k] if kind=='site' else self.tracks[k].center for kind,k in keys]
        options=[[(self.sites[k],6.*(20-len(self.tracks)))] if kind=='site' else self.service_options(self.tracks[k]) for kind,k in keys]
        cost=np.zeros((len(exits),len(exits)));choice={}
        for a,p in enumerate(exits):
            for b,opts in enumerate(options,1):
                vals=[math.dist(p,q)/5+r for q,r in opts];j=int(np.argmin(vals));cost[a,b]=vals[j];choice[a,b]=opts[j][0]
        todo=set(range(1,len(exits)));order=[0]
        while todo:
            b=min(todo,key=lambda b:(cost[order[-1],b],b));order.append(b);todo.remove(b)
        def value(rr):return sum(cost[a,b] for a,b in zip(rr[:-1],rr[1:]))
        best=value(order)
        for _ in range(30):
            winning=None;score=best
            for i in range(1,len(order)-1):
                for j in range(i+1,len(order)):
                    rr=order[:i]+order[i:j+1][::-1]+order[j+1:];v=value(rr)
                    if v<score-1e-7:score=v;winning=rr
            if winning is None:break
            order=winning;best=score
        first=keys[order[1]-1]
        if first[0]=='target' and self.tracks[first[1]].radius>19.5:self.first_choice[first[1]]=choice[0,order[1]].copy()
        self.robot.record(dict(kind='service_route',nodes=[dict(kind=keys[b-1][0],id=keys[b-1][1],entry=choice[a,b].tolist(),exit=np.asarray(exits[b]).tolist()) for a,b in zip(order[:-1],order[1:])],estimated_s=float(best)))
        return [keys[b-1] for b in order[1:]]

    def scan(self,q,site=None):
        channels=[ch for ch in range(1,21) if ch not in self.tracks]
        channels += [ch for ch,t in sorted(self.tracks.items()) if ch not in self.robot.cleared and self.share_worth(t,q)]
        for ch in sorted(channels):
            if ch in self.tracks:self.shared_measures+=1
            self.observe(q,ch)
        self.robot.record(dict(kind='scan_site',site=site,point=np.asarray(q).tolist(),channels=sorted(channels)))

    def adapt(self,remaining):
        if not remaining:return
        if len(self.tracks)==16 and (self.coverage or self.new_policy in ['count','count_service','area_service']):
            self.robot.record(dict(kind='skip_search_count_bound',sites=sorted(remaining)))
            remaining.clear();return
        if not self.coverage:return
        if self.new_policy in ['pool','pool_service']:
            self.pool_adapt(remaining);return
        # Search all pending stations; certify any replacement before paying for it.
        p=self.robot.position.copy()
        # Large savings first, but no unproved station is ever removed.
        for idx in sorted(remaining,key=lambda i:-math.dist(p,self.sites[i])):
            updates=self.coverage.proposal(idx)
            if updates is not None:
                self.coverage.commit(idx,None,updates);remaining.remove(idx);self.removed+=1
                self.robot.record(dict(kind='coverage_remove',site=idx,updated_cells=len(updates)))
        for idx in sorted(remaining,key=lambda i:math.dist(p,self.sites[i])):
            if math.dist(p,self.sites[idx])<2:continue
            updates=self.coverage.proposal(idx,p)
            if updates is None:continue
            # Same unknown-channel scan count as a station, now at the current pose.
            self.scan(p);self.coverage.commit(idx,p,updates);remaining.remove(idx);self.replacements+=1
            self.robot.record(dict(kind='coverage_replace',site=idx,point=p.tolist(),updated_cells=len(updates)))
            break

    def pool_adapt(self,remaining):
        inner=[i for i in remaining if i<8]
        if not inner:return
        p=self.robot.position.copy()
        pending=sorted([t.center for ch,t in self.tracks.items() if ch not in self.robot.cleared],key=lambda q:math.dist(p,q))
        qs=[]
        for q in [p]+pending[:2]:
            if all(math.dist(q,self.coverage.points[i])>2 for i in self.coverage.active) and all(math.dist(q,x)>2 for x in qs):qs.append(q)
        if not qs:return
        proposed=self.coverage.with_points(qs);removed=[]
        for idx in sorted(inner,key=lambda i:-math.dist(p,self.sites[i])):
            updates=proposed.proposal(idx)
            if updates is not None:proposed.commit(idx,None,updates);removed.append(idx)
        if not removed:return
        newids=list(range(len(self.coverage.points),len(proposed.points)))
        def route_length(ids,points):
            pts=np.vstack([points[sorted(ids)],pending]) if pending else points[sorted(ids)]
            rr=open_route(p,set(range(len(pts))),pts,True)
            return length(p,rr,pts)
        old=route_length(remaining,self.sites);new=route_length((remaining-set(removed))|set(newids),proposed.points)
        extra_scans=(len(newids)-len(removed))*(20-len(self.tracks))
        saving=(old-new)/5-6*extra_scans
        self.robot.record(dict(kind='pool_proposal',added=len(newids),removed=removed,estimated_saving_s=float(saving),accepted=saving>20))
        if saving<=20:return
        self.coverage=proposed;self.sites=proposed.points.copy();remaining.difference_update(removed);remaining.update(newids)
        self.removed+=len(removed);self.replacements+=len(newids)
        for i in newids:
            if math.dist(p,self.sites[i])<1e-7:self.scan(p,i);remaining.remove(i);self.visited.add(i)
        self.robot.record(dict(kind='pool_commit',removed=removed,added=[dict(id=i,point=self.sites[i].tolist()) for i in newids]))

    def run(self):
        if self.new_policy=='baseline':return super().run()
        remaining=set(range(len(self.sites)))
        while remaining or any(ch not in self.robot.cleared for ch in self.tracks):
            self.adapt(remaining)
            order=self.joint_order(remaining)
            if not order:break
            self.next_waypoint=None
            if len(order)>1:
                nk,ni=order[1];self.next_waypoint=self.sites[ni] if nk=='site' else self.tracks[ni].center
            kind,k=order[0]
            if kind=='target':self.solve(k)
            else:self.scan(self.sites[k],k);remaining.remove(k);self.visited.add(k)
            if len(self.robot.cleared)==16:break
        self.robot.record(dict(kind='m06_certificate',policy=self.new_policy,coverage=self.coverage.certificate() if self.coverage else None,visited=sorted(self.visited),replacements=self.replacements,removed=self.removed))
        return 'continuous coverage and all discovered cleared'
