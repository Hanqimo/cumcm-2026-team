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
int main(int argc,char**argv){
 try{
 if(argc!=11){std::cerr<<"solver env.csv prefix N base_dt schedule end_s tolerance mode max_picard wall_seconds\n";return 2;}
 std::string envfile=argv[1],prefix=argv[2],mode=argv[8];int n=std::stoi(argv[3]),schedule=std::stoi(argv[5]),maxit=std::stoi(argv[9]);double base=std::stod(argv[4]),end=std::stod(argv[6]),tol=std::stod(argv[7]),budget=std::stod(argv[10]);
 if(n%20||n<20||base<=0||end<=0)throw std::runtime_error("invalid config");
 Grid q(n);Env env(envfile);V T(n+1,28),C(n+1,2.55),mu(n+1),gT(n),zero(n+1,0),src(n+1,0),candC(n+1);
 double rt=root(H*R/K),rc=root(HM*R/5e-9);
 for(int i=0;i<n;i++)gT[i]=(i+.5)*K;
 if(mode=="bessel"){for(int i=0;i<=n;i++){T[i]=28+5*::j0(rt*q.r[i]/R);C[i]=1+.2*::j0(rc*q.r[i]/R);}}
 if(mode=="mms"){for(int i=0;i<=n;i++)C[i]=exactC(q.r[i],0);}
 Linear thermal(n);double prevdt=-1,t=0,cap=1e100;long long steps=0,totalit=0,reject=0;
 double maxres=0,maxratio=0,maxlinear=0,maxupdate=0,maxbalT=0,maxbalC=0,errT=0,errC=0,minT=1e99,maxT=-1e99,minC=1e99,maxC=-1e99;
 long double sumBalT=0,sumBalC=0,absBalT=0,absBalC=0;int maxiter=0;
 auto start=std::chrono::steady_clock::now();std::ofstream out(prefix+"_samples.csv"),diag(prefix+"_diagnostics.csv");
 out<<std::setprecision(17)<<"time_s";for(char f:std::string("TC"))for(int j=0;j<=20;j++)out<<","<<f<<"_"<<j;out<<"\n";
 diag<<std::setprecision(17)<<"time_s,steps,total_picard,max_picard,max_scaled_nonlinear_residual,max_residual_ratio,max_linear_backward_error,cumulative_heat_balance,cumulative_water_balance,min_T,max_T,min_C,max_C\n";
 auto emit=[&](){out<<t;for(const V* v:{&T,&C})for(int j=0;j<=20;j++)out<<","<<(*v)[j*n/20];out<<"\n";diag<<t<<","<<steps<<","<<totalit<<","<<maxiter<<","<<maxres<<","<<maxratio<<","<<maxlinear<<","<<double(sumBalT)<<","<<double(sumBalC)<<","<<*std::min_element(T.begin(),T.end())<<","<<*std::max_element(T.begin(),T.end())<<","<<*std::min_element(C.begin(),C.end())<<","<<*std::max_element(C.begin(),C.end())<<"\n";};
 emit();bool failed=false;std::string why="";
 while(t<end-1e-12){
  double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  if(elapsed>budget){failed=true;why="wall_budget";break;}
  double dt=std::min({scheduled(t,base,schedule),cap,end-t,std::floor(t+1e-10)+1-t});
  if(dt<1e-6){failed=true;why="minimum_dt";break;}
  double tn=t+dt,Te=env.get(env.T,tn),Ce=env.get(env.C,tn);
  if(mode=="equilibrium"){Te=28;Ce=2.55;}
  if(mode=="bessel"){Te=28;Ce=1;}
  if(mode=="mms"){Te=28;double b=.1*std::exp(-tn/100.),cs=1+2*b;Ce=cs+diffus(cs)*(2*b/R)/HM;source_mms(q,tn,src);}
  if(dt!=prevdt){for(int i=0;i<=n;i++)mu[i]=B*q.w[i]/dt;thermal.factor(gT,mu,H);prevdt=dt;}
  thermal.solve(gT,mu,T,H,Te,zero);
  StepDiag sd;bool good=moisture_step(q,C,candC,dt,Ce,src,mode=="bessel",tol,maxit,sd);
  if(!good){reject++;if(mode=="onepicard"){failed=true;why="nonlinear_rejected";maxres=sd.residual;maxratio=sd.ratio;break;}cap=dt/2;continue;}
  double lin=thermal.linear_error(gT);if(lin>1e-12||sd.linear>1e-12)throw std::runtime_error("linear residual");
  double loT=std::min(*std::min_element(T.begin(),T.end()),Te),hiT=std::max(*std::max_element(T.begin(),T.end()),Te),loC=std::min(*std::min_element(C.begin(),C.end()),Ce),hiC=std::max(*std::max_element(C.begin(),C.end()),Ce);
  long double dT=0,dC=0,sourceSum=0;
  for(int i=0;i<=n;i++){
   if(thermal.out[i]<loT-1e-8||thermal.out[i]>hiT+1e-8||(mode!="mms"&&(candC[i]<loC-1e-9||candC[i]>hiC+1e-9)))throw std::runtime_error("range violation");
   dT+=(long double)q.w[i]*(thermal.out[i]-T[i])*B;dC+=(long double)q.w[i]*(candC[i]-C[i]);sourceSum+=src[i];
   minT=std::min(minT,thermal.out[i]);maxT=std::max(maxT,thermal.out[i]);minC=std::min(minC,candC[i]);maxC=std::max(maxC,candC[i]);
  }
  long double bt=dT-(long double)dt*R*H*(Te-thermal.out[n]),bc=dC-(long double)dt*(R*HM*(Ce-candC[n])+sourceSum);
  maxbalT=std::max(maxbalT,std::abs(double(bt)));maxbalC=std::max(maxbalC,std::abs(double(bc)));sumBalT+=bt;sumBalC+=bc;absBalT+=std::abs(bt);absBalC+=std::abs(bc);
  T=thermal.out;C.swap(candC);t=tn;steps++;totalit+=sd.iterations;maxiter=std::max(maxiter,sd.iterations);maxres=std::max(maxres,sd.residual);maxratio=std::max(maxratio,sd.ratio);maxlinear=std::max({maxlinear,sd.linear,lin});maxupdate=std::max(maxupdate,sd.update);
  if(std::abs(t-std::round(t))<1e-10){
   if(mode=="bessel"||mode=="mms")for(int i=0;i<=n;i++){double et=mode=="bessel"?28+5*::j0(rt*q.r[i]/R)*std::exp(-K/B*rt*rt*t/(R*R)):28,ec=mode=="bessel"?1+.2*::j0(rc*q.r[i]/R)*std::exp(-5e-9*rc*rc*t/(R*R)):exactC(q.r[i],t);errT=std::max(errT,std::abs(T[i]-et));errC=std::max(errC,std::abs(C[i]-ec));}
   emit();if(int(std::round(t))%300==0){out.flush();diag.flush();std::cout<<"time "<<t<<" steps "<<steps<<" wall "<<elapsed<<std::endl;}
  }
 }
 save_full(prefix+"_final_state.csv",q,T,C,t);
 std::ofstream js(prefix+"_stats.json");js<<std::setprecision(17)<<"{\n\"completed\":"<<(failed?"false":"true")<<",\"reason\":\""<<why<<"\",\"N\":"<<n<<",\"base_dt\":"<<base<<",\"schedule\":"<<schedule<<",\"end_time\":"<<t<<",\"mode\":\""<<mode<<"\",\"tolerance\":"<<tol<<",\"steps\":"<<steps<<",\"total_picard\":"<<totalit<<",\"max_picard\":"<<maxiter<<",\"rejected_steps\":"<<reject<<",\"max_scaled_nonlinear_residual\":"<<maxres<<",\"max_residual_ratio\":"<<maxratio<<",\"max_linear_backward_error\":"<<maxlinear<<",\"max_update\":"<<maxupdate<<",\"max_heat_balance\":"<<maxbalT<<",\"max_water_balance\":"<<maxbalC<<",\"sum_heat_balance\":"<<double(sumBalT)<<",\"sum_water_balance\":"<<double(sumBalC)<<",\"sum_abs_heat_balance\":"<<double(absBalT)<<",\"sum_abs_water_balance\":"<<double(absBalC)<<",\"min_T\":"<<minT<<",\"max_T\":"<<maxT<<",\"min_C\":"<<minC<<",\"max_C\":"<<maxC<<",\"exact_max_error_T\":"<<errT<<",\"exact_max_error_C\":"<<errC<<",\"wall_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"\n}\n";
 std::cout<<"done "<<prefix<<" wall "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<" complete "<<!failed<<std::endl;
 return failed?3:0;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 2;}
}
