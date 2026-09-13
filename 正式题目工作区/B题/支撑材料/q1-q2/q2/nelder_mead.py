"""Two-dimensional Nelder-Mead with explicit convergence diagnostics."""
import numpy as np

def minimize(fun,x0,step=20,xatol=.05,fatol=1e-6,maxiter=140):
 x=np.array(x0,dtype=float);s=np.array([x,x+[step,0],x+[0,step]]);v=np.array([fun(x) for x in s]);success=False
 for it in range(maxiter):
  ids=np.argsort(v);s=s[ids];v=v[ids]
  if np.max(np.abs(s[1:]-s[0]))<=xatol and np.ptp(v)<=fatol:success=True;break
  c=s[:2].mean(0);xr=2*c-s[2];fr=fun(xr)
  if fr<v[0]:
   xe=c+2*(xr-c);fe=fun(xe);s[2],v[2]=(xe,fe) if fe<fr else (xr,fr)
  elif fr<v[1]:s[2],v[2]=xr,fr
  else:
   outside=fr<v[2];xc=c+.5*((xr if outside else s[2])-c);fc=fun(xc)
   if fc<(fr if outside else v[2]):s[2],v[2]=xc,fc
   else:s[1:]=s[0]+.5*(s[1:]-s[0]);v[1:]=[fun(z) for z in s[1:]]
 j=int(np.argmin(v));return s[j],{'success':success,'iterations':it+1,'simplex_diameter_m':float(np.max(np.linalg.norm(s-s[j],axis=1))),'simplex_value_spread':float(np.ptp(v))}
