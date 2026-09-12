"""Independent polar-ray interval representation; no C++ boundary arcs reused."""
import numpy as np, math, subprocess,json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=math.pi/180

def ray_points(q,kind,t,n=12001):
 phi=np.linspace(-A,A,n);u=np.c_[np.cos(phi),np.sin(phi)];q=np.array(q);b=u@q
 cuts=[np.full(n,5.),np.full(n,1500.)]
 for radius in ([5] if kind==0 else [1000] if kind==2 else [5,1500]):
  disc=b*b+radius*radius-q@q
  h=np.sqrt(np.maximum(0,disc));valid=disc>=0
  cuts.extend([np.where(valid,b-h,np.nan),np.where(valid,b+h,np.nan)])
 if kind==2:cuts.append(np.divide(q@q,2*b,out=np.full(n,np.nan),where=abs(b)>1e-12))
 if kind==1:
  for theta in [t-A,t+A]:
   v=np.array([math.cos(theta),math.sin(theta)])
   den=u[:,0]*v[1]-u[:,1]*v[0];num=q[0]*v[1]-q[1]*v[0]
   cuts.append(np.divide(num,den,out=np.full(n,np.nan),where=abs(den)>1e-12))
 rr=np.sort(np.stack(cuts,axis=1),axis=1);lo=rr[:,:-1];hi=rr[:,1:];rm=(lo+hi)/2;g=u[:,None,:]*rm[:,:,None];d=np.linalg.norm(g-q,axis=2)
 ok=(lo>=5-1e-8)&(hi<=1500+1e-8)&(hi-lo>1e-9)&np.isfinite(rm)
 if kind==0:ok&=d<=5+1e-8
 elif kind==2:ok&=(d>=1000-1e-8)&(d>=rm-1e-8)
 else:
  ang=np.arctan2(g[:,:,1]-q[1],g[:,:,0]-q[0]);delta=np.arctan2(np.sin(ang-t),np.cos(ang-t));ok&=(d>=5-1e-8)&(d<=1500+1e-8)&(abs(delta)<=A+1e-10)
 return np.concatenate([(u[:,None,:]*lo[:,:,None])[ok],(u[:,None,:]*hi[:,:,None])[ok]])

def certify(q,kind,t):
 geo=json.loads(subprocess.check_output([str(ROOT/'solver'),'geometry',*map(str,q),str(kind),str(t)]));p=ray_points(q,kind,t)
 if not len(p):return {'q':q,'kind':kind,'theta':t,'sample_count':0}
 c=np.array(geo['center']);r=geo['radius_upper'];d=np.linalg.norm(p-c,axis=1)
 # Diameter lower bound from 512 directional extrema of independently generated points.
 dirs=np.c_[np.cos(np.arange(512)*2*math.pi/512),np.sin(np.arange(512)*2*math.pi/512)]
 ids=[]
 for v in dirs:ids.append(int(np.argmax(p@v)))
 v=p[np.unique(ids)];d2=((v[:,None,:]-v[None,:,:])**2).sum(2);lower=math.sqrt(float(d2.max()))/2
 return {'q':q,'kind':kind,'theta':t,'sample_count':len(p),'radius_upper_cpp':r,'sample_diameter_lower':lower,'radius_gap_m':r-lower,'max_sample_outside_m':float(d.max()-r),'cpp_internal_gap_m':r-geo['radius_lower']}

def main():
 cases=[]
 for q in [(932.6,590),(864.316399410232,511.3558109716)]:
  profile=ROOT/'verification'/('profile_'+str(q[0])+'.csv');subprocess.run([str(ROOT/'solver'),'profile',*map(str,q),'20',str(profile)],check=True)
  rows=list(csv.DictReader(profile.open()));indexes=np.linspace(0,len(rows)-1,21).astype(int)
  cases.extend((q,1,float(rows[i]['theta'])) for i in indexes)
  cases.append((q,2,0.))
 cases.extend([((500,0),0,0.),((500,0),1,.3),((0,500),1,-.5)])
 records=[certify(*case) for case in cases]
 Path(ROOT/'verification/independent_geometry.json').write_text(json.dumps(records,indent=2))
 checked=[r for r in records if r['sample_count']]
 assert max(r['max_sample_outside_m'] for r in checked)<1e-5
 print(json.dumps({'cases':len(records),'nonempty':len(checked),'max_sample_outside_m':max(r['max_sample_outside_m'] for r in checked),'max_radius_gap_m':max(r['radius_gap_m'] for r in checked),'max_internal_gap_m':max(r['cpp_internal_gap_m'] for r in checked)},indent=2))
if __name__=='__main__':main()
