"""Belief-sampled one-step policy improvement. No access to real world truth.

Uniform position/radius priors are efficiency assumptions, never certificates.
All physical actions retain bounded-region clearing and whole-cell completion.
"""
import copy
import hashlib
import math
import numpy as np
from joint_strategies import JointPlanner,open_route


class BeliefWorld:
    def __init__(self,targets,robot,salt):
        self.targets=targets
        self.position=tuple(robot.position);self.channel=robot.channel
        self.cleared=set(robot.cleared);self.discovered=set(robot.discovered)
        self.scanned_sites=0;self.virtual=0.;self.salt=salt
    def check_budget(self):
        if self.virtual>50000:raise RuntimeError('rollout cap')
    def record(self,event):pass
    def move(self,p):
        self.virtual+=math.dist(p,self.position)/5;self.position=tuple(p)
    def measure(self,p,c):
        self.move(p);self.virtual+=5+int(c!=self.channel);self.channel=c
        target=self.targets.get(c) if c not in self.cleared else None
        d=math.dist(p,target[:2]) if target is not None else math.inf
        if target is None or d>target[2]:return {'measure_result':'no_signal'}
        self.discovered.add(c)
        if d<=5:return {'measure_result':'near'}
        error=math.sin(.039*p[0]+.021*p[1]+c*2.173+self.salt)
        a=math.degrees(math.atan2(target[1]-p[1],target[0]-p[0]))
        return {'measure_result':'direction','svd_deg':round((a+error)%360,2)%360}
    def clear(self,p,c):
        self.move(p);t=self.targets.get(c)
        success=t is not None and c not in self.cleared and math.dist(p,t[:2])<=20
        self.virtual+=5 if success else 3
        if success:self.cleared.add(c)
        return success


def execute(planner,node):
    kind,c,p=node
    if kind=='scan':planner.at_site_scan(p,force=True)
    else:planner.solve_track(planner.tracks[c])


def finish(planner):
    for _ in range(100):
        planner.robot.check_budget()
        pending=[c for c in planner.tracks if c not in planner.robot.cleared]
        if not pending and not planner.unknown():return planner.robot.virtual
        planner.at_site_scan(planner.robot.position)
        nodes=planner.candidates()
        if not nodes:continue
        order=open_route(planner.robot.position,[n[2] for n in nodes])
        execute(planner,nodes[order[0]])
    raise RuntimeError('rollout exhausted')


class RolloutPlanner(JointPlanner):
    def __init__(self,robot,*,rollout_samples=3,rollout_actions=5,rollout_margin=0.,**kwargs):
        super().__init__(robot,**kwargs)
        self.rollout_samples=rollout_samples;self.rollout_actions=rollout_actions
        self.rollout_margin=rollout_margin;self.rollout_calls=0

    def sample_worlds(self):
        # Seed depends only on the observed history, never the benchmark seed.
        digest=hashlib.sha256(repr((self.robot.position,[(c,len(t.history)) for c,t in self.tracks.items()],self.rollout_calls)).encode()).digest()
        rng=np.random.default_rng(int.from_bytes(digest[:8],'little'))
        unknown=[c for c in range(1,21) if c not in self.robot.discovered]
        radius=1800*np.sqrt(rng.random(12000));angle=rng.uniform(0,2*math.pi,12000)
        particles=np.column_stack([radius*np.cos(angle),radius*np.sin(angle)])
        if unknown and self.coverage.samples[unknown[0]]:
            positions=np.asarray(self.coverage.samples[unknown[0]])
            upper=np.minimum(1500.,np.min(np.linalg.norm(particles[:,None,:]-positions[None,:,:],axis=2),axis=1))
        else:upper=np.full(len(particles),1500.)
        weights=np.maximum(upper-1000.,0.)
        probability=float(np.mean(weights)/500)
        m=len(self.robot.discovered)
        counts=np.arange(max(10,m),17)
        probs=np.array([math.comb(int(n),m)*probability**int(n-m) for n in counts],float)
        if probs.sum()==0:counts=np.array([m]);probs=np.ones(1)
        probs/=probs.sum()
        worlds=[]
        for sample in range(self.rollout_samples):
            targets={}
            for c,t in self.tracks.items():
                if c in self.robot.cleared:continue
                poly=t.poly;tri=poly[1:-1];tri2=poly[2:]
                d1=tri-poly[0];d2=tri2-poly[0]
                area=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])
                positive=np.asarray([h['position'] for h in t.history])
                negative=np.asarray(self.coverage.samples[c])
                for _ in range(100):
                    ids=rng.choice(len(area),size=128,p=area/area.sum())
                    uv=rng.random((128,2));uv[uv.sum(axis=1)>1]=1-uv[uv.sum(axis=1)>1]
                    pts=poly[0]+uv[:,0,None]*d1[ids]+uv[:,1,None]*d2[ids]
                    lower=np.maximum(1000.,np.max(np.linalg.norm(pts[:,None,:]-positive[None,:,:],axis=2),axis=1))
                    upper_r=np.full(128,1500.) if not len(negative) else np.minimum(1500.,np.min(np.linalg.norm(pts[:,None,:]-negative[None,:,:],axis=2),axis=1))
                    ok=np.flatnonzero((upper_r>lower)&(np.linalg.norm(pts,axis=1)<=1800.))
                    if len(ok):
                        mass=upper_r[ok]-lower[ok];j=int(rng.choice(ok,p=mass/mass.sum()));targets[c]=[*pts[j],rng.uniform(lower[j],upper_r[j])];break
                else:raise RuntimeError('belief rejection exhausted')
            count=int(rng.choice(counts,p=probs))-m
            if count:
                channels=rng.choice(unknown,size=count,replace=False)
                ids=rng.choice(len(particles),size=count,p=weights/weights.sum())
                for c,j in zip(channels,ids):targets[int(c)]=[*particles[j],rng.uniform(1000.,upper[j])]
            worlds.append((targets,float(rng.uniform(0,1000))))
        return worlds

    def candidates(self):
        nodes=super().candidates()
        if len(nodes)<=1:return nodes
        order=open_route(self.robot.position,[n[2] for n in nodes])
        # Include baseline choice, nearest alternatives and a search action.
        choices=[order[0]]
        nearest=sorted(range(len(nodes)),key=lambda i:math.dist(self.robot.position,nodes[i][2]))
        scans=[i for i in order if nodes[i][0]=='scan']
        if scans and scans[0] not in choices:choices.append(scans[0])
        for i in nearest:
            if i not in choices:choices.append(i)
            if len(choices)>=self.rollout_actions:break
        self.rollout_calls+=1
        try:worlds=self.sample_worlds()
        except (RuntimeError,ValueError):return [nodes[order[0]]]
        state=copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='robot'})
        scores=[]
        for i in choices:
            costs=[]
            for targets,salt in worlds:
                robot=BeliefWorld(targets,self.robot,salt)
                planner=object.__new__(JointPlanner)
                planner.__dict__=copy.deepcopy(state);planner.robot=robot
                try:
                    execute(planner,nodes[i]);costs.append(finish(planner))
                except (RuntimeError,ArithmeticError,ValueError):costs.append(float('inf'))
            scores.append(float(np.mean(costs)))
        best=int(np.argmin(scores))
        if scores[0]-scores[best]<self.rollout_margin:best=0
        self.robot.record(dict(kind='rollout_decision',alternatives=[dict(kind=nodes[i][0],channel=int(nodes[i][1]),predicted_remaining_s=s if math.isfinite(s) else None) for i,s in zip(choices,scores)],selected=best,samples=len(worlds)))
        return [nodes[choices[best]]]
