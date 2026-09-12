"""Independent cell-centred finite-volume / harmonic face / adaptive BDF check.

Uses half-cell resistances to eliminate surface states, unlike the primary
node-centred midpoint solver. Checks selected physical times, not full precision.
"""
from pathlib import Path
import argparse, json, time, hashlib, sys, platform
import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--N',type=int,default=400);a=p.parse_args();n=a.N
    dest=ROOT/'runs'/f'V04_BDF_N{n}';dest.mkdir(exist_ok=False)
    R=.02;h=25.;hm=8e-7;dr=R/n;r=(np.arange(n)+.5)*dr
    edges=np.arange(n+1)*dr;weights=np.diff(edges**2)/2
    env=np.loadtxt(ROOT/'inputs/environment.csv',delimiter=',',skiprows=1)
    def rhs(t,y):
        u=y.reshape(n,2);T=u[:,0];C=u[:,1]
        B=(650+128*C)*(1450+2736*C/(1+C));k=.21+.38*C/(1+C);D=.0024*np.exp(-.45/C-3850/(T+273.15))
        te=np.interp(t,env[:,0],env[:,1]);ce=np.interp(t,env[:,0],env[:,2])
        FT=np.zeros(n+1);FC=np.zeros(n+1)
        FT[1:n]=edges[1:n]*(2*k[:-1]*k[1:]/(k[:-1]+k[1:]))*np.diff(T)/dr
        FC[1:n]=edges[1:n]*(2*D[:-1]*D[1:]/(D[:-1]+D[1:]))*np.diff(C)/dr
        FT[n]=R*(te-T[-1])/(1/h+dr/(2*k[-1]))
        FC[n]=R*(ce-C[-1])/(1/hm+dr/(2*D[-1]))
        return np.column_stack((np.diff(FT)/weights/B,np.diff(FC)/weights)).ravel()
    sparse=lil_matrix((2*n,2*n),dtype=int)
    for i in range(n):
        sparse[2*i:2*i+2,2*max(0,i-1):2*min(n,i+2)]=1
    times=np.unique(np.r_[0,1,2,5,10,30,60,100,300,600,900,1200,np.arange(1800,10801,1800)])
    start=time.monotonic();sol=solve_ivp(rhs,[0,10800],np.tile([28.,2.55],n),method='BDF',rtol=2e-10,atol=np.tile([2e-10,2e-12],n),jac_sparsity=sparse.tocsr(),max_step=30,t_eval=times)
    assert sol.success,sol.message
    radii=np.linspace(0,R,21);result=[]
    for t,y in zip(sol.t,sol.y.T):
        u=y.reshape(n,2);T=u[:,0];C=u[:,1];kl=.21+.38*C[-1]/(1+C[-1]);dl=.0024*np.exp(-.45/C[-1]-3850/(T[-1]+273.15));te=np.interp(t,env[:,0],env[:,1]);ce=np.interp(t,env[:,0],env[:,2])
        ts=(2*kl/dr*T[-1]+h*te)/(2*kl/dr+h);cs=(2*dl/dr*C[-1]+hm*ce)/(2*dl/dr+hm)
        if t==0:ts=28;cs=2.55
        values=[]
        for field,surface in [(T,ts),(C,cs)]:
            center=(9*field[0]-field[1])/8
            values.extend(np.interp(radii,np.r_[0,r,R],np.r_[center,field,surface]))
        result.append([t,*values])
    np.savetxt(dest/'solution_samples.csv',result,delimiter=',',header=','.join(['time_s']+[f'{s}_{i}' for s in ['T','C'] for i in range(21)]),comments='',fmt='%.17g')
    metadata={'model':'Q2-M01-v01','algorithm':'cell-centred FV; harmonic face conductivity; surface series resistance; scipy BDF','N':n,'completed':sol.success,'nfev':sol.nfev,'njev':sol.njev,'nlu':sol.nlu,'wall_seconds':time.monotonic()-start,'rtol':2e-10,'atol_T':2e-10,'atol_C':2e-12,'max_step_s':30,'python':sys.version,'platform':platform.platform(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'environment_sha256':hashlib.sha256((ROOT/'inputs/environment.csv').read_bytes()).hexdigest(),'validation_status':'pending comparison'}
    (dest/'manifest.json').write_text(json.dumps(metadata,indent=2));(dest/'independent_bdf_snapshot.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(metadata))
if __name__=='__main__':main()
