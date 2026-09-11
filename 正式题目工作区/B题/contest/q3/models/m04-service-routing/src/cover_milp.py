"""Joint optional sensing-stop selection and open routing via bounded MILP."""
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from service_routing import ServicePlanner


def solve_cover_route(points,mandatory,masks,query_cost,time_limit=1.):
    n=len(points);edges=[(i,j) for i in range(n) for j in range(n) if i!=j]
    ne=len(edges);idx={edge:k for k,edge in enumerate(edges)}
    # x directed edges; f single-commodity connectivity flow; y visits; z scans.
    yi=2*ne;zi=yi+n;size=zi+n
    c=np.zeros(size);integrality=np.zeros(size,int)
    lower=np.zeros(size);upper=np.ones(size);upper[ne:2*ne]=n-1
    integrality[:ne]=1;integrality[yi:]=1
    D=np.linalg.norm(np.asarray(points)[:,None,:]-np.asarray(points)[None,:,:],axis=2)/5
    for k,(i,j) in enumerate(edges):c[k]=0. if j==0 else D[i,j]
    c[zi:]=query_cost
    lower[yi]=1
    for j in mandatory:lower[yi+j]=1
    constraints=[];lo=[];hi=[]
    def add(items,l,u):constraints.append(items);lo.append(l);hi.append(u)
    for j in range(n):
        add([(idx[i,j],1.) for i in range(n) if i!=j]+[(yi+j,-1.)],0.,0.)
        add([(idx[j,k],1.) for k in range(n) if k!=j]+[(yi+j,-1.)],0.,0.)
        add([(zi+j,1.),(yi+j,-1.)],-np.inf,0.)
    for j in range(1,n):
        add([(ne+idx[i,j],1.) for i in range(n) if i!=j]+[(ne+idx[j,k],-1.) for k in range(n) if k!=j]+[(yi+j,-1.)],0.,0.)
    for k,(i,j) in enumerate(edges):
        add([(ne+k,1.),(k,-(n-1.))],-np.inf,0.)
        if j==0:upper[ne+k]=0.
    for mask in np.unique(np.asarray(masks,dtype=bool).T,axis=0):
        if not np.any(mask):return None
        add([(zi+j,1.) for j in np.flatnonzero(mask)],1.,np.inf)
    A=lil_matrix((len(constraints),size))
    for i,items in enumerate(constraints):
        for j,value in items:A[i,j]+=value
    result=milp(c,integrality=integrality,bounds=Bounds(lower,upper),
        constraints=LinearConstraint(A.tocsc(),np.asarray(lo),np.asarray(hi)),
        options={'time_limit':time_limit,'mip_rel_gap':.01})
    if result.x is None:return None
    selected={j for j in range(n) if result.x[yi+j]>.5};active=[j for j in range(n) if result.x[zi+j]>.5]
    successors={i:j for k,(i,j) in enumerate(edges) if result.x[k]>.5}
    route=[0]
    for _ in range(n):
        j=successors.get(route[-1])
        if j is None:return None
        if j==0:break
        if j in route:return None
        route.append(j)
    if set(route)!=selected or not set(mandatory).issubset(selected):return None
    if len(np.asarray(masks).T) and not np.all(np.any(np.asarray(masks)[active],axis=0)):return None
    cost=sum(D[a,b] for a,b in zip(route,route[1:]))+query_cost*len(active)
    return dict(route=route[1:],active=active,cost=float(cost),gap=float(result.mip_gap),status=int(result.status))


class MilpPlanner(ServicePlanner):
    def __init__(self,robot,*,milp_seconds=1.,milp_budget=16,**kwargs):
        super().__init__(robot,**kwargs);self.milp_seconds=milp_seconds
        self.milp_budget=milp_budget;self.milp_calls=0

    def candidates(self):
        baseline=super().candidates();unknown=self.unknown()
        if not baseline or not unknown or self.pending_probe is not None or self.milp_calls>=self.milp_budget:return baseline
        _,nodes,_=self.last_plan
        targets=[n for n in nodes if n[0]=='target']
        if not targets:return baseline
        points=[np.asarray(self.robot.position)]+[n[2] for n in targets]
        for q in [n[2] for n in nodes if n[0]=='scan']+[np.asarray(p) for p in self.anchors[1:]]:
            if not any(np.linalg.norm(q-p)<.1 for p in points):points.append(q)
        missing=~self.coverage.covered[unknown[0]]
        masks=np.array([self.coverage.mask(p)[missing] for p in points])
        self.milp_calls+=1
        solution=solve_cover_route(points,range(1,len(targets)+1),masks,6*len(unknown),self.milp_seconds)
        if solution is None or solution['cost']>=self.last_plan[0]/5-1e-6:return baseline
        self.robot.record(dict(kind='joint_cover_milp',predicted_cost_s=solution['cost'],incumbent_cost_s=self.last_plan[0]/5,
            relative_solver_gap=solution['gap'],solver_status=solution['status'],nodes=len(points),mandatory_targets=len(targets)))
        j=0 if 0 in solution['active'] else solution['route'][0]
        if j in solution['active']:return [('scan',-20000-j,points[j])]
        if 1<=j<=len(targets):return [targets[j-1]]
        return baseline
