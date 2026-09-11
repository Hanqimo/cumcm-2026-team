"""Sparse posterior-consistent policy rollouts, using observation history only."""
import copy,math
import numpy as np
from service_routing import ServicePlanner
from belief_components import BeliefWorld,RolloutPlanner,execute


def complete(planner):
    for _ in range(120):
        planner.robot.check_budget()
        pending=[c for c in planner.tracks if c not in planner.robot.cleared]
        if not pending and not planner.unknown():return planner.robot.virtual
        gain=planner.scan_gain;planner.scan_gain=2.
        try:planner.at_site_scan(planner.robot.position)
        finally:planner.scan_gain=gain
        nodes=planner.candidates()
        if nodes:execute(planner,nodes[0])
    raise RuntimeError('Lookahead completion cap')


class LookaheadPlanner(ServicePlanner):
    sample_worlds=RolloutPlanner.sample_worlds

    def __init__(self,robot,*,rollout_samples=2,rollout_actions=3,rollout_margin=20.,**kwargs):
        super().__init__(robot,**kwargs)
        self.rollout_samples=rollout_samples;self.rollout_actions=rollout_actions
        self.rollout_margin=rollout_margin;self.rollout_calls=0;self.rollout_stages=set()

    def candidates(self):
        result=super().candidates();stage=len(self.robot.cleared)//4
        if not result or self.pending_probe is not None or stage>2 or stage in self.rollout_stages:return result
        if self.last_plan is None or len(self.last_plan[1])<2:return result
        self.rollout_stages.add(stage);self.rollout_calls+=1
        _,nodes,order=self.last_plan
        choices=list(result)
        ordered=[nodes[i] for i in order]
        scans=[n for n in ordered if n[0]=='scan']
        for node in (scans[:1]+ordered):
            if any(node[0]==old[0] and node[1]==old[1] and np.linalg.norm(node[2]-old[2])<.1 for old in choices):continue
            choices.append(node)
            if len(choices)>=self.rollout_actions:break
        try:worlds=self.sample_worlds()
        except (RuntimeError,ValueError):return result
        state=copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='robot'})
        scores=[]
        for node in choices:
            costs=[]
            for targets,salt in worlds:
                robot=BeliefWorld(targets,self.robot,salt)
                planner=object.__new__(ServicePlanner);planner.__dict__=copy.deepcopy(state);planner.robot=robot
                planner.cover_trials=1;planner.cover_radii=None;planner.transit_probes=False
                planner.service_route=False;planner.pending_probe=None;planner.merge_trials=False
                try:execute(planner,node);costs.append(complete(planner))
                except (RuntimeError,ArithmeticError,ValueError):costs.append(float('inf'))
            scores.append(float(np.mean(costs)))
        best=int(np.argmin(scores))
        if not math.isfinite(scores[best]) or scores[0]-scores[best]<self.rollout_margin:best=0
        self.robot.record(dict(kind='posterior_lookahead',stage=stage,samples=len(worlds),
            alternatives=[dict(kind=n[0],channel=int(n[1]),predicted_remaining_s=s if math.isfinite(s) else None) for n,s in zip(choices,scores)],
            selected=best,prior='uniform area/radius and source count 10..16; planning only'))
        return [choices[best]]
