"""Check general-model geometry and normalization identities; does not solve the design optimization."""
from pathlib import Path
import numpy as np, json, math
p=Path(__file__).resolve().parents[1]
alpha=math.pi/180
rng=np.random.default_rng(20260912)
a=rng.uniform(0,3400,100000);phi=rng.uniform(-math.pi,math.pi,len(a));t=rng.uniform(5.001,1499.999,len(a))
x=a+t*np.cos(phi);y=t*np.sin(phi)
cart=x*x+y*y<=1800**2
D=1800**2-a*a*np.sin(phi)**2
lo=np.maximum(5,-a*np.cos(phi)-np.sqrt(np.maximum(D,0)));hi=np.minimum(1500,-a*np.cos(phi)+np.sqrt(np.maximum(D,0)))
ray=(D>=0)&(t>lo)&(t<hi)
assert np.array_equal(cart,ray)
# Compare C1 via radial integration and independent integration of A(r)h(r).
def moments(a,beta,n=192):
 z,w=np.polynomial.legendre.leggauss(n);angles=beta+alpha*z
 D=1800**2-a*a*np.sin(angles)**2
 lo=np.maximum(5,-a*np.cos(angles)-np.sqrt(np.maximum(D,0)))
 hi=np.minimum(1500,-a*np.cos(angles)+np.sqrt(np.maximum(D,0)))
 ok=(D>=0)&(hi>lo)
 def F(t):
  return np.where(t<=1000,t*t/2,500000+(750*(t*t-1000000)-(t**3-1000**3)/3)/500)
 C=alpha*np.sum(w*np.where(ok,F(hi)-F(lo),0))
 if not np.any(ok): return 0.,0.
 rmin=max(1000.,float(np.min(lo[ok])))
 r=(1500+rmin)/2+(1500-rmin)*z/2
 A=.5*alpha*np.sum(w[None,:]*np.where(ok,np.maximum(np.minimum(r[:,None],hi)**2-lo**2,0),0),axis=1)
 other=(1500-rmin)/1000*np.sum(w*A)
 return float(C),float(other)
cs={}
for a,b in [(0,0),(1500,0),(2500,-math.pi),(2500,0),(3299,-math.pi),(3300,-math.pi),(1700,1.2),(1700,-1.2)]:
 c,d=moments(a,b);cs[str((a,b))]={'C1_ray':c,'C1_radius_area':d,'relative_difference':abs(c-d)/c if c else 0}
 assert (abs(c-d)/c if c else abs(d))<2e-4
base=alpha*((1500**3-1000**3)/(3*500)-25)
assert abs(cs[str((0,0))]['C1_ray']-base)<1e-8
assert cs[str((2500,0))]['C1_ray']==0
assert cs[str((3300,-math.pi))]['C1_ray']==0
assert abs(cs[str((1700,1.2))]['C1_ray']-cs[str((1700,-1.2))]['C1_ray'])<1e-8
out={'scope':'Model algebra and geometry only; no optimization or general solver validation','ray_cartesian_membership_samples':len(a) if hasattr(a,'__len__') else 100000,'membership_disagreements':int(np.sum(cart!=ray)),'C1_cross_checks':cs,'baseline_C1_analytic':base,'checks_passed':True}
(p/'verification/a_beta_model_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
