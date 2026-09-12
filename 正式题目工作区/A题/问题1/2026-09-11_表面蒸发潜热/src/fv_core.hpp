#pragma once
// M01-v01 / A01: node-centred cylindrical finite volumes, backward Euler, Picard.
// Compile: clang++ -O3 -std=c++17 solver.cpp -o solver (no fast-math).
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>
using V=std::vector<double>;
constexpr double R=.02, B=820.*2600., K=.36, H=25., HM=8e-7;
struct Grid{
 int n; double dr; V r,w;
 Grid(int n_):n(n_),dr(R/n),r(n+1),w(n+1){
  for(int i=0;i<=n;i++){r[i]=i*dr;double a=i? (i-.5)*dr:0,b=i<n?(i+.5)*dr:R;w[i]=(b*b-a*a)/2;}
 }
};
struct Linear{
 int n; V diag,cp,inv,rhs,out;
 Linear(int n_):n(n_),diag(n+1),cp(n+1),inv(n+1),rhs(n+1),out(n+1){}
 void factor(const V&g,const V&mu,double h){
  for(int i=0;i<=n;i++){
   diag[i]=mu[i]+(i?g[i-1]:0)+(i<n?g[i]:R*h);
   double p=diag[i]-(i?g[i-1]*(-cp[i-1]):0);
   if(!(p>0)||!std::isfinite(p))throw std::runtime_error("invalid Thomas pivot");
   inv[i]=1/p;cp[i]=i<n?-g[i]*inv[i]:0;
  }
 }
 void solve(const V&g,const V&mu,const V&old,double h,double ext,const V&source){
  for(int i=0;i<=n;i++){rhs[i]=mu[i]*old[i]+source[i]+(i==n?R*h*ext:0);out[i]=(rhs[i]+(i?g[i-1]*out[i-1]:0))*inv[i];}
  for(int i=n-1;i>=0;i--)out[i]-=cp[i]*out[i+1];
 }
 double linear_error(const V&g)const{
  double num=0,an=0,xn=0,fn=0;
  for(int i=0;i<=n;i++){double z=diag[i]*out[i]-(i?g[i-1]*out[i-1]:0)-(i<n?g[i]*out[i+1]:0)-rhs[i];
   num=std::max(num,std::abs(z));an=std::max(an,diag[i]+(i?g[i-1]:0)+(i<n?g[i]:0));xn=std::max(xn,std::abs(out[i]));fn=std::max(fn,std::abs(rhs[i]));}
  return num/(an*xn+fn+1e-300);
 }
};
double diffus(double c){if(!(c>0)||!std::isfinite(c))throw std::runtime_error("nonpositive moisture");return 7e-9*std::exp(-.89/c);}
void conduct(const Grid&q,const V&c,V&g,bool constant){
 double left=constant?5e-9:diffus(c[0]);
 for(int i=0;i<q.n;i++){double right=constant?5e-9:diffus(c[i+1]);g[i]=(i+.5)*(left+right)/2;left=right;}
}
struct StepDiag{int iterations=0;double update=0,residual=0,ratio=0,linear=0;};
bool moisture_step(const Grid&q,const V&old,V&next,double dt,double ext,const V&src,
                   bool constant,double tol,int limit,StepDiag&st){
 V mu(q.n+1),cur=old,g(q.n),ng(q.n);for(int i=0;i<=q.n;i++)mu[i]=q.w[i]/dt;
 conduct(q,cur,g,constant);Linear a(q.n);
 for(int it=1;it<=limit;it++){
  a.factor(g,mu,HM);a.solve(g,mu,old,HM,ext,src);
  st.linear=std::max(st.linear,a.linear_error(g));
  conduct(q,a.out,ng,constant);double upd=0,res=0,amp=0;
  for(int i=0;i<=q.n;i++){
   double f=mu[i]*(a.out[i]-old[i])-src[i];
   if(i)f+=ng[i-1]*(a.out[i]-a.out[i-1]);
   if(i<q.n)f-=ng[i]*(a.out[i+1]-a.out[i]);else f-=R*HM*(ext-a.out[i]);
   double diagonal=mu[i]+(i?ng[i-1]:0)+(i<q.n?ng[i]:R*HM);
   res=std::max(res,std::abs(f)/diagonal);upd=std::max(upd,std::abs(a.out[i]-cur[i]));amp=std::max(amp,std::abs(a.out[i]));
  }
  double eps=tol*(1+amp);st.iterations=it;st.update=upd;st.residual=res;st.ratio=res/eps;
  next=a.out;
  if(upd<=eps&&res<=eps)return true;
  cur=a.out;g.swap(ng);
 }
 return false;
}
struct Env{
 V ts,T,C;
 Env(const std::string&f){std::ifstream in(f);if(!in)throw std::runtime_error("environment missing");std::string s;std::getline(in,s);while(std::getline(in,s)){std::replace(s.begin(),s.end(),',',' ');std::istringstream row(s);double t,a,c;if(row>>t>>a>>c){ts.push_back(t);T.push_back(a);C.push_back(c);}}}
 double get(const V&v,double t)const{auto it=std::upper_bound(ts.begin(),ts.end(),t);int i=std::max(0,std::min(int(ts.size())-2,int(it-ts.begin())-1));double z=(t-ts[i])/(ts[i+1]-ts[i]);return v[i]*(1-z)+v[i+1]*z;}
};
double root(double bi){double a=0,b=2.40482555769577;for(int i=0;i<80;i++){double x=(a+b)/2;if(x*::j1(x)-bi*::j0(x)>0)b=x;else a=x;}return (a+b)/2;}
double exactC(double r,double t){double b=.1*std::exp(-t/100.);return 1+b+b*(r/R)*(r/R);}
double mmsf(double r,double t){double b=.1*std::exp(-t/100.),x=r/R,c=1+b+b*x*x,d=diffus(c);return -b/100.*(1+x*x)-4*b/(R*R)*(d+b*x*x*d*.89/(c*c));}
void source_mms(const Grid&q,double t,V&s){
 constexpr double z[3]={-.7745966692414834,0,.7745966692414834}, wt[3]={5./9,8./9,5./9};
 for(int i=0;i<=q.n;i++){double a=i?(i-.5)*q.dr:0,b=i<q.n?(i+.5)*q.dr:R,mid=(a+b)/2,half=(b-a)/2;s[i]=0;for(int k=0;k<3;k++){double r=mid+half*z[k];s[i]+=half*wt[k]*r*mmsf(r,t);}}
}
double scheduled(double t,double base,int schedule){
 if(!schedule)return base;
 // Prescribed piecewise time refinement; unchanged BE scheme, no extrapolation.
 double mult=t<2?1:t<8?4:t<32?16:t<128?64:t<512?128:256;
 return base*mult;
}
void save_full(const std::string&path,const Grid&q,const V&T,const V&C,double t){
 std::ofstream f(path);f<<std::setprecision(17)<<"time_s,r_m,T_C,C_kg_kg\n";for(int i=0;i<=q.n;i++)f<<t<<","<<q.r[i]<<","<<T[i]<<","<<C[i]<<"\n";
}
