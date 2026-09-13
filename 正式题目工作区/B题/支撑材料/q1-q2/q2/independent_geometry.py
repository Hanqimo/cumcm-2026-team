"""独立极坐标区间采样及有限支撑圆枚举，仅供几何核验。"""
import itertools,math
import numpy as np
A=math.pi/180

def independent_points(a,b,q,kind,t,n=8001):
 phi=np.linspace(-A,A,n);u=np.c_[np.cos(phi),np.sin(phi)];q=np.array(q);B=math.radians(b);center=np.array([-a*math.cos(B),a*math.sin(B)])
 cuts=[np.full(n,5.),np.full(n,1500.)]
 def circlecuts(c,r):
  proj=u@c;disc=proj*proj+r*r-c@c;h=np.sqrt(np.maximum(0,disc));good=disc>=0
  cuts.extend([np.where(good,proj-h,np.nan),np.where(good,proj+h,np.nan)])
 circlecuts(center,1800)
 for r in ([5] if kind==0 else [1000] if kind==2 else [5,1500]):circlecuts(q,r)
 if kind==2:
  v=u@q;cuts.append(np.divide(q@q,2*v,out=np.full(n,np.nan),where=abs(v)>1e-12))
 if kind==1:
  for ang in [t-A,t+A]:
   v=np.array([math.cos(ang),math.sin(ang)]);den=u[:,0]*v[1]-u[:,1]*v[0];num=q[0]*v[1]-q[1]*v[0]
   cuts.append(np.divide(num,den,out=np.full(n,np.nan),where=abs(den)>1e-12))
 rr=np.sort(np.stack(cuts,axis=1),axis=1);lo=rr[:,:-1];hi=rr[:,1:];mid=(lo+hi)/2
 g=u[:,None,:]*mid[:,:,None];d=np.linalg.norm(g-q,axis=2)
 ok=np.isfinite(mid)&(lo>=5-1e-8)&(hi<=1500+1e-8)&(hi-lo>1e-9)&(np.linalg.norm(g-center,axis=2)<=1800+1e-8)
 if kind==0:ok&=d<=5+1e-8
 elif kind==2:ok&=(d>=1000-1e-8)&(d>=mid-1e-8)
 else:
  ang=np.arctan2(g[:,:,1]-q[1],g[:,:,0]-q[0]);delta=np.arctan2(np.sin(ang-t),np.cos(ang-t));ok&=(d>=5-1e-8)&(d<=1500+1e-8)&(abs(delta)<=A+1e-10)
 return np.concatenate([(u[:,None,:]*lo[:,:,None])[ok],(u[:,None,:]*hi[:,:,None])[ok]])

def exact_finite_radius(v):
 if len(v)<2:return 0.
 v=v-v.mean(axis=0);n=len(v);pairs=np.array(list(itertools.combinations(range(n),2)))
 cc=(v[pairs[:,0]]+v[pairs[:,1]])*.5;rr=np.sum((v[pairs[:,0]]-cc)**2,axis=1)
 if n>=3:
  tri=np.array(list(itertools.combinations(range(n),3)));a=v[tri[:,0]];b=v[tri[:,1]]-a;c=v[tri[:,2]]-a
  det=2*(b[:,0]*c[:,1]-b[:,1]*c[:,0]);ok=abs(det)>1e-12;a=a[ok];b=b[ok];c=c[ok];det=det[ok]
  b2=(b*b).sum(1);c2=(c*c).sum(1);z=np.c_[(b2*c[:,1]-b[:,1]*c2)/det,(b[:,0]*c2-b2*c[:,0])/det]
  cc=np.r_[cc,a+z];rr=np.r_[rr,(z*z).sum(1)]
 for i in np.argsort(rr):
  if np.max(((cc[i]-v)**2).sum(1)-rr[i])<=1e-8:return math.sqrt(float(rr[i]))
 raise RuntimeError('no enclosing circle')
