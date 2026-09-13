"""Calibrated scenario profiles and an observation-only Robot for Q3/Q4.

This is an empirical practice-model approximation, not the official generator.
Legacy fixtures and frozen strategies are never changed. No network/UI imports.
"""
import math, hashlib, struct, json
from pathlib import Path
import numpy as np

def fixture(seed,problem=4,profile=None,n=None,k=None,error_mode=None):
    profile=profile or json.loads(Path(__file__).with_name('calibrated_profile.json').read_text(encoding='utf-8'))
    rng=np.random.default_rng(seed)
    n=int(rng.integers(10,17)) if n is None else int(n)
    if problem==3:k=0
    elif k is None:
        law=profile['q4_directional_count_model']
        if law=='uniform_0_N':k=int(rng.integers(0,n+1))
        elif law=='uniform_1_N':k=int(rng.integers(1,n+1))
        elif law=='uniform_0_Nminus1':k=int(rng.integers(0,n))
        elif law=='uniform_1_Nminus1':k=int(rng.integers(1,n))
        elif law=='binomial_N_half':k=int(rng.binomial(n,.5))
        elif law=='forced_mixed_binomial':k=1+int(rng.binomial(n-2,.5))
        else:raise ValueError(law)
    assert 10<=n<=16 and 0<=k<=n
    channels=rng.choice(np.arange(1,21),n,replace=False);sources={}
    for i,ch in enumerate(channels):
        a=rng.uniform(0,2*np.pi);r=1800*np.sqrt(rng.random())
        heading=rng.uniform(0,2*np.pi);radius=rng.uniform(1000,1500)
        sources[int(ch)]=dict(point=[float(r*np.cos(a)),float(r*np.sin(a))],radius=float(radius),heading=float(heading) if i<k else None)
    return dict(seed=seed,n=n,directional=k,problem=problem,sources=sources,errors=error_mode or 'sin',layout='area',profile=profile.copy())

class World:
    def __init__(self,data):
        self.data={**data,'sources':{int(ch):s for ch,s in data['sources'].items()}}
        # Optional conditioning of research hypotheses. Never emitted by fixture().
        # Exact spatial keys preserve persistent readings; no rounding of positions.
        self.error_anchors={}
        for anchor in data.get('error_anchors',[]):
            key=self.anchor_key(anchor['point'],anchor['channel'])
            value=float(anchor['error'])
            if not math.isfinite(value) or not -1<=value<=1:raise ValueError('Invalid bounded error anchor')
            if key in self.error_anchors and self.error_anchors[key]!=value:raise ValueError('Conflicting persistent error anchors')
            self.error_anchors[key]=value
        self.position=np.zeros(2);self.channel=1;self.cleared=set();self.discovered=set()
        self.virtual=0.;self.distance=0.;self.measures=0;self.switches=0;self.failures=0;self.events=[]
    @staticmethod
    def anchor_key(q,ch):
        if len(q)!=2 or not all(math.isfinite(float(v)) for v in q):raise ValueError('Invalid anchor point')
        if int(ch)!=ch or not 1<=int(ch)<=20:raise ValueError('Invalid anchor channel')
        return (int(ch),float(q[0]) or 0.,float(q[1]) or 0.)
    def move(self,q):
        q=np.asarray(q,float);d=float(np.linalg.norm(q-self.position));self.distance+=d;self.virtual+=d/5;self.position=q.copy()
        if self.virtual>349000 or len(self.events)>12000:raise RuntimeError('local action/time cap')
    def error(self,q,ch):
        if self.error_anchors:
            key=self.anchor_key(q,ch)
            if key in self.error_anchors:return self.error_anchors[key]
        mode=self.data['errors'];seed=self.data['seed']
        if mode=='sin':return math.sin(q[0]*.017+q[1]*.031+ch*2.7+seed)
        if mode=='plus':return 1.
        if mode=='minus':return -1.
        if mode=='checker':return 1. if (math.floor(q[0]/10)+math.floor(q[1]/10)+ch)%2 else -1.
        if mode=='hash_uniform':
            # Stable same-point noise; 0 and -0 are normalized. Not Python's salted hash.
            raw=struct.pack('<qqdd',seed,int(ch),float(q[0]) or 0.,float(q[1]) or 0.)
            u=int.from_bytes(hashlib.blake2b(raw,digest_size=8).digest(),'little')/2**64
            return 2*u-1
        raise ValueError(mode)
    def measure(self,q,ch):
        self.move(q);sw=int(ch!=self.channel);self.channel=ch;self.measures+=1;self.switches+=sw;self.virtual+=5+sw
        s=self.data['sources'].get(ch);z={'measure_result':'no_signal'}
        if s is not None and ch not in self.cleared:
            delta=self.position-np.array(s['point']);d=float(np.linalg.norm(delta));h=s['heading']
            visible=h is None or float(delta@np.array([math.cos(h),math.sin(h)]))>=-1e-10
            if d<=s['radius'] and visible:
                self.discovered.add(ch)
                z={'measure_result':'near'} if d<=5 else {'measure_result':'direction','svd_deg':round((math.degrees(math.atan2(-delta[1],-delta[0]))+self.error(self.position,ch))%360,2)%360}
        self.events.append(dict(kind='measure',point=self.position.tolist(),channel=int(ch),result=z.copy(),time_s=self.virtual))
        return z
    def clear(self,q,ch):
        self.move(q);s=self.data['sources'].get(ch)
        ok=s is not None and ch not in self.cleared and math.dist(q,s['point'])<=20
        self.virtual+=5 if ok else 3
        if ok:self.cleared.add(ch)
        else:self.failures+=1
        self.events.append(dict(kind='clear',point=self.position.tolist(),channel=int(ch),success=bool(ok),time_s=self.virtual))
        return bool(ok)

def condition_q3_history(data,actions):
    """Return a shared World that exactly explains and has replayed a Q3 prefix.

    This is an existence construction for bounded persistent errors, not posterior
    sampling. All hypothesized sources (including cleared ones) must be supplied.
    Neither the real fixture nor its hidden parameters are needed by callers.
    Past cost is retained: compare future costs after subtracting world.virtual.
    """
    world=World(data)
    sources=world.data['sources']
    if not 10<=len(sources)<=16:raise ValueError('Q3 hypothesis source count outside 10..16')
    for ch,s in sources.items():
        World.anchor_key(s['point'],ch)
        if s.get('heading') is not None:raise ValueError('Q3 requires omnidirectional sources')
        if not 1000<=float(s['radius'])<=1500 or math.hypot(*s['point'])>1800:raise ValueError('Invalid Q3 source geometry')
    for index,a in enumerate(actions):
        q=a['point'];ch=int(a['channel']);World.anchor_key(q,ch)
        if a['kind']=='measure':
            z=a['result']
            if z['measure_result']=='direction':
                s=sources.get(ch)
                if s is None or ch in world.cleared:raise ValueError(f'Positive history lacks active source at {index}')
                delta=np.asarray(q,float)-np.asarray(s['point'],float)
                angle=math.degrees(math.atan2(-delta[1],-delta[0]))
                reading=float(z['svd_deg'])
                if not math.isfinite(reading) or not 0<=reading<360:raise ValueError('Invalid bearing reading')
                key=World.anchor_key(q,ch)
                if key not in world.error_anchors:
                    diff=(reading-angle+180)%360-180
                    lo=max(-1.,diff-.005);hi=min(1.,diff+.005)
                    if lo>hi:raise ValueError(f'History bearing outside error bound at {index}')
                    value=(lo+hi)/2
                    if round((angle+value)%360,2)%360!=reading:raise ValueError(f'No rounding witness at {index}')
                    world.error_anchors[key]=value
                # Shared measure below checks reception, near, previous clears,
                # and exact repeated readings with this same fixed error.
            actual=world.measure(q,ch)
            if actual!=z:raise ValueError(f'Incompatible measurement history at {index}')
        elif a['kind']=='clear':
            if world.clear(q,ch)!=a['success']:raise ValueError(f'Incompatible clear history at {index}')
        else:raise ValueError(f'Unknown history action at {index}')
    world.data['error_anchors']=[dict(channel=ch,point=[x,y],error=e) for (ch,x,y),e in world.error_anchors.items()]
    return world

class Robot:
    def __init__(self,world):self.__world=world;self.scanned_sites=0;self.decisions=[]
    @property
    def position(self):return self.__world.position.copy()
    @property
    def channel(self):return self.__world.channel
    @property
    def cleared(self):return frozenset(self.__world.cleared)
    @property
    def discovered(self):return frozenset(self.__world.discovered)
    def measure(self,q,ch):return self.__world.measure(q,ch)
    def clear(self,q,ch):return self.__world.clear(q,ch)
    def record(self,event):self.decisions.append(event)
    def check_budget(self):
        if self.__world.virtual>349000:raise RuntimeError('local time cap')

class ReplayRobot:
    """Exact logged-action replay. Rejects deviations; cannot evaluate new actions."""
    def __init__(self,actions):
        self.__actions=[x for x in actions if x[0] in ('/measure','/clear')];self.index=0
        self.position=np.zeros(2);self.channel=1;self.cleared=set();self.discovered=set();self.scanned_sites=0;self.virtual=0
    def step(self,endpoint,q,ch):
        if self.index>=len(self.__actions):raise AssertionError('Replay exhausted; no off-policy inference allowed')
        path,p,z=self.__actions[self.index]
        assert path==endpoint and ch==p['channel'] and np.allclose(q,[p['position']['x'],p['position']['y']],rtol=0,atol=1e-6),f'Replay diverged at {self.index}'
        self.index+=1;self.position=np.asarray(q,float);self.virtual=z['virtual_time_s'];return z
    def measure(self,q,ch):
        z=self.step('/measure',q,ch);self.channel=ch
        if z['measure_result']!='no_signal':self.discovered.add(ch)
        return {k:z[k] for k in ('measure_result','svd_deg') if k in z}
    def clear(self,q,ch):
        ok=self.step('/clear',q,ch)['clear_result']=='success'
        if ok:self.cleared.add(ch)
        return ok
    def record(self,event):pass
    def check_budget(self):pass
    def assert_complete(self):assert self.index==len(self.__actions)
