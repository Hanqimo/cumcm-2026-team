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
int PRIOR=0; // 0 uniform, -1 density favouring small R, +1 favouring large R
// Triangular alternatives have positive density on the open interval.
double tail(double d){double u=clamp((d-1000)/500,0.0,1.0);return PRIOR==0?1-u:(PRIOR<0?(1-u)*(1-u):1-u*u);}
struct Prim {bool circle;P p;double r;int sign;}; // circle sign=+1 inside, -1 outside; line p dot g<=r
struct Arc {P o;double r,l,h;};
struct Shape {vector<P> points;vector<Arc> arcs;};
using Region=vector<Prim>;
void line(Region&v,P n,double b){double d=norm(n);if(d>1e-14)v.push_back({false,n*(1/d),b/d,1});}
void circle(Region&v,P o,double r,int sign=1){v.push_back({true,o,r,sign});}
void wedge(Region&v,P o,double t){P lo=unit(t-A),hi=unit(t+A);P n1={lo.y,-lo.x},n2={-hi.y,hi.x};line(v,n1,dot(n1,o));line(v,n2,dot(n2,o));}
Region base(){Region v;circle(v,{0,0},1500);circle(v,{0,0},5,-1);wedge(v,{0,0},0);return v;}
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
 for(auto p:all)if(p.circle){double d=norm(p.p);if(d>p.r+1e-10){double t=angle(p.p),a=asin(p.r/d);for(double f:{wrap(t-a),wrap(t+a)})if(f>-A&&f<A)cuts.push_back(f);}}
 uniquev(cuts);return cuts;}
double mass(const Region&v,const Shape&s,P q,int kind,int na,int nr){if(s.points.empty())return 0;auto ts=spatial_breaks(v,s,q);auto gn=gauss(na),gr=gauss(nr);double sum=0;for(size_t ti=0;ti+1<ts.size();ti++){double mid=(ts[ti]+ts[ti+1])/2,half=(ts[ti+1]-ts[ti])/2;for(auto [z,w]:gn){P u=unit(mid+half*z);vector<double>rs={5,1000,1500};for(auto p:v)addray(rs,p,u);addray(rs,{true,q,1000,1},u);double den=2*dot(q,u);if(abs(den)>1e-12){double r=norm2(q)/den;if(r>5&&r<1500)rs.push_back(r);}uniquev(rs,1e-8);double radial=0;for(size_t j=0;j+1<rs.size();j++){double rm=(rs[j]+rs[j+1])/2,rh=(rs[j+1]-rs[j])/2;if(!feasible(v,u*rm,1e-8))continue;for(auto [zz,ww]:gr){double r=rm+rh*zz,d=norm(u*r-q),val=0;if(kind==0)val=tail(r);if(kind==1)val=tail(max(r,d));if(kind==2)val=tail(r)-tail(max(r,d));radial+=ww*rh*r*val;}}sum+=w*half*radial;}}
 return max(0.0,sum);}
Region feedback(P q,int kind,double theta=0){Region v=base();if(kind==0)circle(v,q,5);else if(kind==1){circle(v,q,1500);circle(v,q,5,-1);wedge(v,q,theta);}else{circle(v,q,1000,-1);line(v,q*2,norm2(q));}return v;}
vector<double> feedback_breaks(P q){Region v=base();circle(v,q,1500);circle(v,q,5,-1);Shape s=boundary(v);vector<double>ts={0,2*PI};vector<double>phis;for(auto p:s.points)phis.push_back(pos(angle(p-q)));for(auto ar:s.arcs){double d=norm(ar.o-q);if(d>ar.r+1e-10){double t=angle(q-ar.o),z=acos(ar.r/d);for(double b:{pos(t-z),pos(t+z)})for(int k=0;k<2;k++){double p=b+2*PI*k;if(p>=ar.l-1e-10&&p<=ar.h+1e-10)phis.push_back(pos(angle(ar.o+unit(p)*ar.r-q)));}}else if(d<1e-9&&ar.h-ar.l>2*PI-1e-6)for(int j=0;j<8;j++)phis.push_back(j*PI/4);}
 for(double t:phis){ts.push_back(pos(t-A));ts.push_back(pos(t+A));}uniquev(ts,1e-11);return ts;}
struct Val {double p=0,loss=0,plo=0,p20=0,rmean=0;Val operator+(Val b)const{return{p+b.p,loss+b.loss,plo+b.plo,p20+b.p20,rmean+b.rmean};}Val operator*(double s)const{return{p*s,loss*s,plo*s,p20*s,rmean*s};}};
struct Settings {int ns=4,nr=6,nt=4,depth=2;double rel=2e-4;};
struct Result {P q;double J=0,Jlo=0,ph=0,pn=0,pa=0,p20=0,rmean=0,safe=0;int calls=0;};
struct Eval {P q;Settings set;double Z;int calls=0;double maxgap=0;vector<array<double,7>> profile;
 Val at(double theta){calls++;auto v=feedback(q,1,theta);auto s=boundary(v);double m=mass(v,s,q,1,set.ns,set.nr)/(2*A*Z);if(m<=0)return{};auto c=continuous_mec(s);maxgap=max(maxgap,c.hi-c.lo);return{m,m*PI*c.hi*c.hi,m*PI*c.lo*c.lo,m*(c.hi<=20),m*c.hi};}
 Val quadrature(double l,double h,int n){Val v;double mid=(l+h)/2,half=(h-l)/2;for(auto [z,w]:gauss(n))v=v+at(mid+half*z)*(half*w);return v;}
 Val adaptive(double l,double h,int dep){Val low=quadrature(l,h,set.nt),high=quadrature(l,h,set.nt*2);double err=abs(low.loss-high.loss),tol=set.rel*max(1.0,abs(high.loss));if(dep>=set.depth||(err<=tol&&abs(high.p-low.p)<set.rel*.1&&abs(high.p20-low.p20)<max(2e-6,set.rel*.2)))return high;double m=(l+h)/2;return adaptive(l,m,dep+1)+adaptive(m,h,dep+1);}
};
double normalizer(){auto v=base();auto s=boundary(v);return mass(v,s,{0,0},0,6,12);}
double safe_margin(P q){ // exact endpoint/radial reduction for the full sector
 double worst=-1e99;for(double r:{5.,1000.,1500.}){double mincos=1e99;for(double t:{-A,A})mincos=min(mincos,dot(q,unit(t)));double away=pos(angle(q)+PI);for(int k=-1;k<=0;k++){double t=away+2*PI*k;if(t>=-A&&t<=A)mincos=-norm(q);}double d=sqrt(max(0.0,norm2(q)+r*r-2*r*mincos));worst=max(worst,d-max(1000.,r));}return -worst;}
Result evaluate(P q,Settings set){double Z=normalizer();Eval e{q,set,Z};Result out;out.q=q;out.safe=safe_margin(q);for(int kind:{0,2}){auto v=feedback(q,kind);auto s=boundary(v);double p=mass(v,s,q,kind,set.ns*2,set.nr*2)/Z;if(p>0){auto c=continuous_mec(s);out.J+=p*PI*c.hi*c.hi;out.Jlo+=p*PI*c.lo*c.lo;out.p20+=p*(c.hi<=20);out.rmean+=p*c.hi;}if(kind==0)out.ph=p;else out.pn=p;}
 auto ts=feedback_breaks(q);
 if(set.depth>=5){vector<double> roots;auto rf=[&](double t){auto sh=boundary(feedback(q,1,t));if(sh.points.empty())return 0.;return continuous_mec(sh).hi-20.;};for(size_t i=0;i+1<ts.size();i++){double l=ts[i],h=ts[i+1],delta=(h-l)*1e-9;double prev=l+delta,fp=rf(prev);for(int j=1;j<=40;j++){double now=j==40?h-delta:l+(h-l)*j/40.,fn=rf(now);if(fp*fn<0){double a=prev,b=now,fa=fp;for(int k=0;k<38;k++){double m=(a+b)/2,fm=rf(m);if(fa*fm<=0)b=m;else{a=m;fa=fm;}}roots.push_back((a+b)/2);}prev=now;fp=fn;}}ts.insert(ts.end(),roots.begin(),roots.end());uniquev(ts,1e-12);}
 Val total;for(size_t i=0;i+1<ts.size();i++)if(ts[i+1]-ts[i]>1e-12)total=total+e.adaptive(ts[i],ts[i+1],0);out.J+=total.loss;out.Jlo+=total.plo;out.pa=total.p;out.p20+=total.p20;out.rmean+=total.rmean;out.calls=e.calls;return out;}
Settings settings(int level){if(level==0)return{2,4,2,0,.01};if(level==1)return{4,6,3,1,.001};if(level==2)return{6,10,4,3,2e-5};if(level==3)return{10,14,6,5,2e-7};if(level==4)return{14,20,8,7,2e-9};return{20,28,10,9,2e-11};}
void header(ostream&o){o<<"x,y,J,J_lower,P_H,P_N,P_A,P20,E_radius,safe_margin,angle_calls\n";}
void row(ostream&o,Result r){o<<setprecision(15)<<r.q.x<<","<<r.q.y<<","<<r.J<<","<<r.Jlo<<","<<r.ph<<","<<r.pn<<","<<r.pa<<","<<r.p20<<","<<r.rmean<<","<<r.safe<<","<<r.calls<<"\n";}
bool useful(P q){double t=clamp(angle(q),-A,A),r=clamp(dot(q,unit(t)),5.,1500.);return norm(q-unit(t)*r)<=1500+1e-8&&norm(q)>=1;}
int main(int argc,char**argv){if(argc<2)return 1;string mode=argv[1];if(mode=="eval"){P q={stod(argv[2]),stod(argv[3])};int level=argc>4?stoi(argv[4]):2;PRIOR=argc>5?stoi(argv[5]):0;header(cout);row(cout,evaluate(q,settings(level)));}
 else if(mode=="batch"){ifstream f(argv[2]);ofstream out(argv[3]);int level=stoi(argv[4]);PRIOR=argc>5?stoi(argv[5]):0;header(out);string s;int k=0;while(getline(f,s)){replace(s.begin(),s.end(),',',' ');stringstream ss(s);P q;if(!(ss>>q.x>>q.y))continue;if(!useful(q))continue;auto r=evaluate(q,settings(level));row(out,r);out.flush();if(++k%25==0)cerr<<k<<" evaluated, last J="<<r.J<<"\n";}}
 else if(mode=="profile"){P q={stod(argv[2]),stod(argv[3])};int n=stoi(argv[4]);ofstream out(argv[5]);Settings st=settings(3);Eval e{q,st,normalizer()};out<<"theta,pdf,radius_upper,radius_lower,center_x,center_y\n";auto ts=feedback_breaks(q);for(size_t i=0;i+1<ts.size();i++)for(int j=0;j<n;j++){double t=ts[i]+(ts[i+1]-ts[i])*(j+.5)/n;auto v=feedback(q,1,t);auto sh=boundary(v);double m=mass(v,sh,q,1,10,14)/(2*A*e.Z);if(m<=0)continue;auto c=continuous_mec(sh);out<<setprecision(15)<<t<<","<<m<<","<<c.hi<<","<<c.lo<<","<<c.c.x<<","<<c.c.y<<"\n";}}
 else if(mode=="geometry"){P q={stod(argv[2]),stod(argv[3])};int k=stoi(argv[4]);double t=stod(argv[5]);auto v=feedback(q,k,t);auto s=boundary(v);auto c=continuous_mec(s);cout<<setprecision(15)<<"{\"radius_lower\":"<<c.lo<<",\"radius_upper\":"<<c.hi<<",\"center\":["<<c.c.x<<","<<c.c.y<<"],\"points\":[";for(size_t i=0;i<s.points.size();i++){if(i)cout<<",";cout<<"["<<s.points[i].x<<","<<s.points[i].y<<"]";}cout<<"],\"arcs\":[";for(size_t i=0;i<s.arcs.size();i++){auto a=s.arcs[i];if(i)cout<<",";cout<<"["<<a.o.x<<","<<a.o.y<<","<<a.r<<","<<a.l<<","<<a.h<<"]";}cout<<"]}\n";}

 else if(mode=="branches"){P q={stod(argv[2]),stod(argv[3])};double z=normalizer();cout<<"kind,probability,radius_lower,radius_upper,center_x,center_y,loss_contribution\n";for(int kind:{0,2}){auto v=feedback(q,kind);auto sh=boundary(v);double p=mass(v,sh,q,kind,20,24)/z;auto c=continuous_mec(sh);cout<<setprecision(15)<<kind<<","<<p<<","<<c.lo<<","<<c.hi<<","<<c.c.x<<","<<c.c.y<<","<<p*PI*c.hi*c.hi<<"\n";}}
 else if(mode=="mc"){P q={stod(argv[2]),stod(argv[3])};int n=stoi(argv[4]);unsigned seed=argc>5?stoi(argv[5]):812371;mt19937_64 gen(seed);uniform_real_distribution<double> U(0,1);auto regN=feedback(q,2),regH=feedback(q,0);auto cn=continuous_mec(boundary(regN)),ch=continuous_mec(boundary(regH));double sum=0,sum2=0,maxres=-1e99,sumr=0;int nh=0,nn=0,n20=0,invalid=0;vector<double> radii;radii.reserve(n);for(int i=0;i<n;i++){double r,phi;do{r=sqrt(25+(2250000-25)*U(gen));phi=(2*U(gen)-1)*A;}while(U(gen)>tail(r));P g=unit(phi)*r;double R=max(1000.,r)+(1500-max(1000.,r))*U(gen);double d=norm(g-q);MEC c;Region v;if(d<=5){nh++;c=ch;v=regH;}else if(d>R){nn++;c=cn;v=regN;}else{double theta=angle(g-q)+(2*U(gen)-1)*A;v=feedback(q,1,theta);auto sh=boundary(v);if(sh.points.empty())invalid++;c=continuous_mec(sh);}if(!feasible(v,g,1e-6))invalid++;maxres=max(maxres,norm(g-c.c)-c.hi);double l=PI*c.hi*c.hi;sum+=l;sum2+=l*l;sumr+=c.hi;n20+=c.hi<=20;radii.push_back(c.hi);}sort(radii.begin(),radii.end());double mean=sum/n,se=sqrt(max(0.,sum2/n-mean*mean)/(n-1));cout<<setprecision(15)<<"{\"n\":"<<n<<",\"seed\":"<<seed<<",\"mean_area\":"<<mean<<",\"standard_error\":"<<se<<",\"P_H\":"<<(double)nh/n<<",\"P_N\":"<<(double)nn/n<<",\"P20\":"<<(double)n20/n<<",\"mean_radius\":"<<sumr/n<<",\"radius_median\":"<<radii[n/2]<<",\"radius_p90\":"<<radii[(int)(n*.9)]<<",\"radius_p95\":"<<radii[(int)(n*.95)]<<",\"radius_p99\":"<<radii[(int)(n*.99)]<<",\"max_truth_coverage_residual\":"<<maxres<<",\"invalid\":"<<invalid<<"}\n";}
 else if(mode=="selftest"){auto s=boundary(base());auto c=continuous_mec(s);cout<<setprecision(15)<<"Z="<<normalizer()<<" radius="<<c.hi<<" points="<<s.points.size()<<" arcs="<<s.arcs.size()<<" gap="<<c.hi-c.lo<<"\n";for(P q:vector<P>{{700,500},{900,400},{1200,500},{0,0}})cout<<q.x<<","<<q.y<<" safe="<<safe_margin(q)<<"\n";}
}
