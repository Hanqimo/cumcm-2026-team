"""Offline-only action ledger, never consumed by online decision code."""
import math


def traced_world(base):
    class TraceWorld(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.categories={};self.last_clear_time=0.;self.probes=0;self.merges=0
            self.action_trace=[];self.decision_trace=[]
        def add_cost(self,kind,before,before_d):
            item=self.categories.setdefault(kind,dict(count=0,time_s=0.,distance_m=0.))
            item['count']+=1;item['time_s']+=self.virtual-before;item['distance_m']+=self.distance_m-before_d
        def measure(self,point,channel):
            kind='known_measure' if channel in self.discovered else 'unknown_measure'
            before,d=self.virtual,self.distance_m
            result=super().measure(point,channel);self.add_cost(kind,before,d)
            self.action_trace.append(dict(kind='measure',point=list(point),channel=channel,response=result,time_s=self.virtual))
            return result
        def clear(self,point,channel):
            before,d=self.virtual,self.distance_m
            result=super().clear(point,channel);self.add_cost('clear',before,d)
            if result:self.last_clear_time=self.virtual
            self.action_trace.append(dict(kind='clear',point=list(point),channel=channel,success=result,time_s=self.virtual))
            return result
        def record(self,event):
            if event['kind']=='transit_probe':self.probes+=1
            if event['kind']=='merge_scans':self.merges+=1
            if event['kind'] in ['optical_region','optical_failure_update']:
                from shapely import wkt
                from shapely.geometry import Point
                assert wkt.loads(event['wkt']).distance(Point(self.targets[event['channel']][:2]))<1e-6, event
            if event['kind'] in ['optical_decision','optical_failure_update','value_bundle','joint_cover_milp','posterior_lookahead','clear_certificate','completion_certificate']:self.decision_trace.append(event)
            return super().record(event)
        def ledger(self):
            assert abs(sum(c['time_s'] for c in self.categories.values())-self.virtual)<1e-7
            return dict(categories=self.categories,tail_after_last_clear_s=self.virtual-self.last_clear_time,transit_probes=self.probes,planned_merges=self.merges)
    return TraceWorld
