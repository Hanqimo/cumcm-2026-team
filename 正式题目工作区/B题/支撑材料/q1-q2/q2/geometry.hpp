#pragma once
// General a,beta extension. Internal coordinates: S1 origin, first bearing +x.
// Model source remains O-centered; TARGET_CENTER preserves its disk exactly.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
constexpr double PI=3.1415926535897932384626433832795, A=PI/180, RMAX=1500, RMIN=1000, INNER=5;
struct P {double x=0,y=0; P operator+(P b)const{return{x+b.x,y+b.y};} P operator-(P b)const{return{x-b.x,y-b.y};} P operator*(double s)const{return{x*s,y*s};}};
double dot(P a,P b){return a.x*b.x+a.y*b.y;} double cross(P a,P b){return a.x*b.y-a.y*b.x;} double norm2(P a){return dot(a,a);} double norm(P a){return sqrt(norm2(a));} P unit(double t){return{cos(t),sin(t)};} double angle(P a){return atan2(a.y,a.x);} double wrap(double t){return remainder(t,2*PI);} double pos(double t){t=fmod(t,2*PI);return t<0?t+2*PI:t;}
// Uniform prior R in [1000,1500]. One shared radius for both observations.
double tail(double d){return 1-clamp((d-1000)/500,0.0,1.0);}
struct Prim {bool circle;P p;double r;int sign;}; // circle sign=+1 inside, -1 outside; line p dot g<=r
struct Arc {P o;double r,l,h;};
struct Shape {vector<P> points;vector<Arc> arcs;};
using Region=vector<Prim>;
void line(Region&v,P n,double b){double d=norm(n);if(d>1e-14)v.push_back({false,n*(1/d),b/d,1});}
void circle(Region&v,P o,double r,int sign=1){v.push_back({true,o,r,sign});}
void wedge(Region&v,P o,double t){P lo=unit(t-A),hi=unit(t+A);P n1={lo.y,-lo.x},n2={-hi.y,hi.x};line(v,n1,dot(n1,o));line(v,n2,dot(n2,o));}
double SCENARIO_A=0,SCENARIO_BETA=0,ZC=0; P TARGET_CENTER;
Region base(){Region v;circle(v,TARGET_CENTER,1800);circle(v,{0,0},1500);circle(v,{0,0},5,-1);wedge(v,{0,0},0);return v;}
bool feasible(const Region&v,P g,double tol=2e-7){for(auto s:v){double f=s.circle?s.sign*(norm(g-s.p)-s.r):dot(s.p,g)-s.r;if(f>tol)return false;}return true;}
vector<P> intersect(Prim a,Prim b){vector<P>v;if(!a.circle&&!b.circle){double d=cross(a.p,b.p);if(abs(d)>1e-12)v.push_back({(a.r*b.p.y-a.p.y*b.r)/d,(a.p.x*b.r-a.r*b.p.x)/d});return v;}
 if(!a.circle)swap(a,b);
 if(!b.circle){double signed_d=b.r-dot(b.p,a.p);double z=a.r*a.r-signed_d*signed_d;if(z>=-1e-6){P c=a.p+b.p*signed_d, u={-b.p.y,b.p.x};double t=sqrt(max(0.0,z));v.push_back(c+u*t);if(t>1e-9)v.push_back(c-u*t);}return v;}
 double d=norm(b.p-a.p);if(d<1e-10||d>a.r+b.r+1e-7||d<abs(a.r-b.r)-1e-7)return v;P u=(b.p-a.p)*(1/d);double t=(a.r*a.r-b.r*b.r+d*d)/(2*d),z=a.r*a.r-t*t;if(z< -1e-5)return v;P c=a.p+u*t,n={-u.y,u.x};double h=sqrt(max(0.0,z));v.push_back(c+n*h);if(h>1e-9)v.push_back(c-n*h);return v;}
void uniquev(vector<double>&v,double tol=1e-10){sort(v.begin(),v.end());v.erase(unique(v.begin(),v.end(),[&](double x,double y){return abs(x-y)<tol;}),v.end());}
Shape boundary(const Region&v){Shape s;for(size_t i=0;i<v.size();i++){auto p=v[i];vector<double>ts;P d={-p.p.y,p.p.x};for(size_t j=0;j<v.size();j++)if(i!=j)for(auto x:intersect(p,v[j]))ts.push_back(p.circle?pos(angle(x-p.p)):dot(d,x));uniquev(ts);
 if(p.circle){if(ts.empty())ts={0};size_t n=ts.size();for(size_t k=0;k<n;k++){double l=ts[k],h=k+1<n?ts[k+1]:ts[0]+2*PI;if(h-l<1e-12)continue;P mid=p.p+unit((l+h)/2)*p.r;if(feasible(v,mid)){s.arcs.push_back({p.p,p.r,l,h});s.points.push_back(p.p+unit(l)*p.r);s.points.push_back(p.p+unit(h)*p.r);}}}
 else for(size_t k=0;k+1<ts.size();k++){P x=p.p*p.r+d*ts[k],y=p.p*p.r+d*ts[k+1];if(feasible(v,(x+y)*.5)){s.points.push_back(x);s.points.push_back(y);}}
 } vector<P>pts;for(auto x:s.points){bool exists=false;for(auto y:pts)if(norm(x-y)<1e-6){exists=true;break;}if(!exists&&feasible(v,x,1e-5))pts.push_back(x);}s.points=pts;return s;}
struct Disk {P c;double r=-1;};
bool covers(Disk d,P p){return d.r>=0&&norm(p-d.c)<=d.r+2e-8;}
Disk two(P a,P b){return{(a+b)*.5,norm(a-b)*.5};}
Disk three(P a,P b,P c){Disk best;best.r=1e99;for(auto d:{two(a,b),two(a,c),two(b,c)})if(covers(d,a)&&covers(d,b)&&covers(d,c)&&d.r<best.r)best=d;
 if(best.r<1e98)return best;P u=b-a,v=c-a;double den=2*cross(u,v);if(abs(den)<1e-14)return best;P z={(norm2(u)*v.y-u.y*norm2(v))/den,(u.x*norm2(v)-norm2(u)*v.x)/den};return{a+z,norm(z)};}
Disk finite_mec(vector<P>ps){if(ps.empty())return{{0,0},0};std::mt19937 gen(1729);shuffle(ps.begin(),ps.end(),gen);Disk d;for(size_t i=0;i<ps.size();i++)if(!covers(d,ps[i])){d={ps[i],0};for(size_t j=0;j<i;j++)if(!covers(d,ps[j])){d=two(ps[i],ps[j]);for(size_t k=0;k<j;k++)if(!covers(d,ps[k]))d=three(ps[i],ps[j],ps[k]);}}return d;}
P farthest(const Shape&s,P c){P best=s.points.empty()?P{}:s.points[0];double b=norm2(best-c);auto check=[&](P p){double v=norm2(p-c);if(v>b){b=v;best=p;}};for(auto p:s.points)check(p);for(auto a:s.arcs){double t=pos(angle(a.o-c));for(int k=-1;k<=2;k++){double v=t+2*PI*k;if(v>=a.l-1e-12&&v<=a.h+1e-12)check(a.o+unit(v)*a.r);}}return best;}
struct MEC {P c;double lo=0,hi=0;int it=0;};
MEC continuous_mec(const Shape&s,double eps=1e-7){if(s.points.empty())return{};vector<P>v=s.points;MEC out;for(int it=0;it<80;it++){Disk d=finite_mec(v);P p=farthest(s,d.c);double h=norm(p-d.c);out={d.c,d.r,max(h,d.r),it};if(out.hi-out.lo<=eps)return out;v.push_back(p);}return out;}
// Gauss-Legendre nodes on [-1,1], generated independently of integration intervals.
map<int,vector<pair<double,double>>> gcache;
vector<pair<double,double>> gauss(int n){if(gcache.count(n))return gcache[n];vector<pair<double,double>>v;for(int i=0;i<n;i++){double z=cos(PI*(i+.75)/(n+.5)),dp=0;for(int j=0;j<30;j++){double p0=1,p1=z;for(int k=2;k<=n;k++){double p=((2*k-1)*z*p1-(k-1)*p0)/k;p0=p1;p1=p;}dp=n*(z*p1-p0)/(z*z-1);double dz=p1/dp;z-=dz;if(abs(dz)<1e-15)break;}v.push_back({z,2/((1-z*z)*dp*dp)});}return gcache[n]=v;}
void addray(vector<double>&cuts,Prim p,P u){if(p.circle){double b=dot(u,p.p),disc=b*b+p.r*p.r-norm2(p.p);if(disc>=0){double h=sqrt(disc);for(double r:{b-h,b+h})if(r>5&&r<1500)cuts.push_back(r);}}else{double den=dot(p.p,u);if(abs(den)>1e-14){double r=p.r/den;if(r>5&&r<1500)cuts.push_back(r);}}}
vector<double> spatial_breaks(const Region&v,const Shape&s,P q){vector<double>cuts={-A,A};auto add=[&](P p){double t=angle(p);if(t>-A&&t<A)cuts.push_back(t);};for(auto p:s.points)add(p);
 vector<Prim>all=v;circle(all,q,1000); // kink in the integrated weight
 line(all,q*2,norm2(q));circle(all,{0,0},1000);for(size_t i=0;i<all.size();i++)for(size_t j=i+1;j<all.size();j++)for(auto p:intersect(all[i],all[j]))add(p);
 for(auto p:all)if(p.circle){double d=norm(p.p);if(d>p.r+1e-10){double t=angle(p.p),a=asin(p.r/d);for(double f:{wrap(t-a),wrap(t+a)})if(f>-A&&f<A)cuts.push_back(f);}}
 uniquev(cuts);return cuts;}
double mass(const Region&v,const Shape&s,P q,int kind,int na,int nr){if(s.points.empty())return 0;auto ts=spatial_breaks(v,s,q);auto gn=gauss(na),gr=gauss(nr);double sum=0;for(size_t ti=0;ti+1<ts.size();ti++){double mid=(ts[ti]+ts[ti+1])/2,half=(ts[ti+1]-ts[ti])/2;for(auto [z,w]:gn){P u=unit(mid+half*z);vector<double>rs={5,1000,1500};for(auto p:v)addray(rs,p,u);addray(rs,{true,q,1000,1},u);double den=2*dot(q,u);if(abs(den)>1e-12){double r=norm2(q)/den;if(r>5&&r<1500)rs.push_back(r);}uniquev(rs,1e-8);double radial=0;for(size_t j=0;j+1<rs.size();j++){double rm=(rs[j]+rs[j+1])/2,rh=(rs[j+1]-rs[j])/2;if(!feasible(v,u*rm,1e-8))continue;for(auto [zz,ww]:gr){double r=rm+rh*zz,d=norm(u*r-q),val=0;if(kind==0)val=tail(r);if(kind==1)val=tail(max(r,d));if(kind==2)val=tail(r)-tail(max(r,d));radial+=ww*rh*r*val;}}sum+=w*half*radial;}}
 return max(0.0,sum);}
Region feedback(P q,int kind,double theta=0){Region v=base();if(kind==0)circle(v,q,5);else if(kind==1){circle(v,q,1500);circle(v,q,5,-1);wedge(v,q,theta);}else{circle(v,q,1000,-1);line(v,q*2,norm2(q));}return v;}
vector<double> feedback_breaks(P q){Region v=base();circle(v,q,1500);circle(v,q,5,-1);Shape s=boundary(v);vector<double>ts={0,2*PI};vector<double>phis;for(auto p:s.points)phis.push_back(pos(angle(p-q)));for(auto ar:s.arcs){double d=norm(ar.o-q);if(d>ar.r+1e-10){double t=angle(q-ar.o),z=acos(ar.r/d);for(double b:{pos(t-z),pos(t+z)})for(int k=0;k<2;k++){double p=b+2*PI*k;if(p>=ar.l-1e-10&&p<=ar.h+1e-10)phis.push_back(pos(angle(ar.o+unit(p)*ar.r-q)));}}else if(d<1e-9&&ar.h-ar.l>2*PI-1e-6)for(int j=0;j<8;j++)phis.push_back(j*PI/4);}
 Region beyond=base();circle(beyond,q,1500);circle(beyond,q,20,-1);Shape bs=boundary(beyond);
 for(auto p:bs.points)phis.push_back(pos(angle(p-q)));
 for(auto ar:bs.arcs){double d=norm(ar.o-q);if(d>ar.r+1e-10){double t=angle(q-ar.o),z=acos(ar.r/d);for(double b:{pos(t-z),pos(t+z)})for(int k=-1;k<=2;k++){double p=b+2*PI*k;if(p>=ar.l-1e-10&&p<=ar.h+1e-10)phis.push_back(pos(angle(ar.o+unit(p)*ar.r-q)));}}}
 for(double t:phis){ts.push_back(pos(t-A));ts.push_back(pos(t+A));}uniquev(ts,1e-11);return ts;}

struct Settings {int ns=4,nr=6,nt=4,depth=2;double rel=2e-4;};

double normalizer(){auto v=base();auto s=boundary(v);return mass(v,s,{0,0},0,64,16);}

Settings settings(int level){if(level>=6)return{28,36,14,11,2e-13};if(level==0)return{2,4,2,0,.01};if(level==1)return{4,6,3,1,.001};if(level==2)return{6,10,4,3,2e-5};if(level==3)return{10,14,6,5,2e-7};if(level==4)return{14,20,8,7,2e-9};return{20,28,10,9,2e-11};}
