// Frozen geometric/probability kernel; never modifies the adopted implementation.
#define main baseline_main
#include "../inputs/base_solver.cpp"
#undef main

struct TrialValue {
 double p=0,j=0,finish=0,onsite=0;
 TrialValue operator+(TrialValue b)const{return{p+b.p,j+b.j,finish+b.finish,onsite+b.onsite};}
 TrialValue operator*(double k)const{return{p*k,j*k,finish*k,onsite*k};}
};
struct TrialEvaluator {
 P q;Settings st;int scan=8,calls=0,capped=0,roots_count=0;double gap=0;
 double threshold(double theta){auto s=boundary(feedback(q,1,theta));return s.points.empty()?1e6:continuous_mec(s).hi-20.;}
 vector<double> breaks(){
  auto t=feedback_breaks(q);vector<double> extra;
  for(size_t i=0;i+1<t.size();i++){
   double l=t[i],h=t[i+1];if(h-l<1e-11)continue;
   double edge=min((h-l)*1e-7,1e-9),prev=l+edge,fp=threshold(prev);
   for(int k=1;k<=scan;k++){
    double now=k==scan?h-edge:l+(h-l)*k/scan,fn=threshold(now);
    if(fp*fn<0){double a=prev,b=now,fa=fp;
     for(int z=0;z<40;z++){double m=(a+b)/2,fm=threshold(m);if(fa*fm<=0)b=m;else{a=m;fa=fm;}}
     extra.push_back((a+b)/2);
    }
    prev=now;fp=fn;
   }
  }
  roots_count=extra.size();t.insert(t.end(),extra.begin(),extra.end());uniquev(t,1e-12);return t;
 }
 TrialValue at(double theta){
  calls++;auto v=feedback(q,1,theta);auto s=boundary(v);
  double m=mass(v,s,q,1,st.ns,st.nr)/(2*A*ZC);if(m<=0)return{};
  auto c=continuous_mec(s);gap=max(gap,c.hi-c.lo);
  bool optical=norm(farthest(s,q)-q)<=20.;
  return{m,m*c.hi,m*(c.hi<=20.),m*optical};
 }
 TrialValue quad(double l,double h,int n){TrialValue v;for(auto [z,w]:gauss(n))v=v+at((l+h)/2+(h-l)*z/2)*(w*(h-l)/2);return v;}
 TrialValue adaptive(double l,double h,int depth){
  auto low=quad(l,h,st.nt),high=quad(l,h,st.nt*2);
  bool ok=abs(low.j-high.j)<=st.rel*max(1.,abs(high.j))&&abs(low.p-high.p)<=st.rel*.1&&abs(low.finish-high.finish)<=st.rel*.1&&abs(low.onsite-high.onsite)<=st.rel*.1;
  if(ok)return high;if(depth>=st.depth){capped++;return high;}
  double m=(l+h)/2;return adaptive(l,m,depth+1)+adaptive(m,h,depth+1);
 }
};
double distance_to_initial(P q){
 auto v=base();if(feasible(v,q,1e-9))return 0.;auto s=boundary(v);double best=1e99;
 for(P x:s.points)best=min(best,norm(q-x));
 for(auto ar:s.arcs){double theta=pos(angle(q-ar.o));for(int k=-1;k<=2;k++)if(theta+2*PI*k>=ar.l&&theta+2*PI*k<=ar.h)best=min(best,abs(norm(q-ar.o)-ar.r));}
 for(auto p:v)if(!p.circle){P proj=q-p.p*(dot(p.p,q)-p.r);if(feasible(v,proj,1e-7))best=min(best,norm(proj-q));}
 return best;
}
void trial_header(){cout<<"x,y,J,P_finish,P_onsite,P_H,P_N,P_normal,P_finish_N,P_finish_normal,probability_residual,mec_gap,angle_calls,root_count,depth_capped,distance_K1,x_global,y_global\n";}
void trial_evaluate(P q,int level,int scan){
 auto st=settings(level);TrialEvaluator e{q,st,scan};TrialValue total;double ph=0,pn=0,fn=0;
 for(int kind:{0,2}){auto v=feedback(q,kind);auto s=boundary(v);double p=mass(v,s,q,kind,st.ns*2,st.nr*2)/ZC;if(kind==0)ph=p;else pn=p;
  if(p<=0)continue;auto c=continuous_mec(s);e.gap=max(e.gap,c.hi-c.lo);bool optical=norm(farthest(s,q)-q)<=20.;
  total=total+TrialValue{p,p*c.hi,p*(c.hi<=20.),p*optical};if(kind==2)fn=p*(c.hi<=20.);
 }
 auto t=e.breaks();TrialValue normal;for(size_t i=0;i+1<t.size();i++)if(t[i+1]-t[i]>1e-12)normal=normal+e.adaptive(t[i],t[i+1],0);total=total+normal;
 cout<<setprecision(15)<<q.x<<","<<q.y<<","<<total.j<<","<<total.finish<<","<<total.onsite<<","<<ph<<","<<pn<<","<<normal.p<<","<<fn<<","<<normal.finish<<","<<total.p-1<<","<<e.gap<<","<<e.calls<<","<<e.roots_count<<","<<e.capped<<","<<distance_to_initial(q)<<","<<(SCENARIO_A+cos(SCENARIO_BETA)*q.x-sin(SCENARIO_BETA)*q.y)<<","<<(sin(SCENARIO_BETA)*q.x+cos(SCENARIO_BETA)*q.y)<<"\n";
}
void trial_mc(P q,int n,int seed){
 mt19937_64 gen(seed);uniform_real_distribution<double> u(0,1);double sumj=0,sumj2=0;int done=0,onsite=0,nh=0,nn=0,invalid=0;double maxres=-1e99;
 auto shN=boundary(feedback(q,2)),shH=boundary(feedback(q,0));auto cn=continuous_mec(shN),ch=continuous_mec(shH);
 for(int i=0;i<n;i++){
  double r,phi,R;do{r=sqrt(25+(2250000-25)*u(gen));phi=(2*u(gen)-1)*A;R=1000+500*u(gen);}while(r>R||norm(unit(phi)*r-TARGET_CENTER)>1800);
  P g=unit(phi)*r;double d=norm(g-q);MEC c;Shape s;Region v;
  if(d<=5){nh++;c=ch;s=shH;v=feedback(q,0);}else if(d>R){nn++;c=cn;s=shN;v=feedback(q,2);}else{double theta=angle(g-q)+(2*u(gen)-1)*A;v=feedback(q,1,theta);s=boundary(v);c=continuous_mec(s);}
  if(s.points.empty()||!feasible(v,g,1e-6)){invalid++;continue;}
  bool optical=norm(farthest(s,q)-q)<=20.;double j=c.hi;sumj+=j;sumj2+=j*j;done+=c.hi<=20.;onsite+=optical;maxres=max(maxres,norm(g-c.c)-c.hi);
 }
 double mean=sumj/n,p=double(done)/n;
 cout<<setprecision(15)<<"{\"n\":"<<n<<",\"seed\":"<<seed<<",\"J_mean\":"<<mean<<",\"J_se\":"<<sqrt(max(0.,sumj2/n-mean*mean)/(n-1))<<",\"P_finish\":"<<p<<",\"P_finish_se\":"<<sqrt(p*(1-p)/n)<<",\"P_onsite\":"<<double(onsite)/n<<",\"P_H\":"<<double(nh)/n<<",\"P_N\":"<<double(nn)/n<<",\"invalid\":"<<invalid<<",\"max_truth_outside\":"<<maxres<<"}\n";
}
int frozen_trial_main(int argc,char**argv){
 if(argc<4)return 1;SCENARIO_A=stod(argv[1]);SCENARIO_BETA=stod(argv[2])*PI/180;TARGET_CENTER={-SCENARIO_A*cos(SCENARIO_BETA),SCENARIO_A*sin(SCENARIO_BETA)};ZC=normalizer();if(!(ZC>0))return 2;string mode=argv[3];
 if(mode=="eval"){trial_header();trial_evaluate({stod(argv[4]),stod(argv[5])},stoi(argv[6]),argc>7?stoi(argv[7]):8);}
 else if(mode=="stream"){trial_header();cout.flush();double x,y;int level,scan;while(cin>>x>>y>>level>>scan){trial_evaluate({x,y},level,scan);cout.flush();}}
 else if(mode=="mc")trial_mc({stod(argv[4]),stod(argv[5])},stoi(argv[6]),stoi(argv[7]));
 else if(mode=="baseline"){auto r=evaluate({stod(argv[4]),stod(argv[5])},settings(stoi(argv[6])));cout<<setprecision(15)<<r.rmean<<"\n";}
 else if(mode=="cuts"){TrialEvaluator e{{stod(argv[4]),stod(argv[5])},settings(5),stoi(argv[6])};auto t=e.breaks();cout<<setprecision(15)<<"[";for(size_t i=0;i<t.size();i++)cout<<(i?",":"")<<t[i];cout<<"]\n";}
 else if(mode=="geometry"){auto s=boundary(feedback({stod(argv[4]),stod(argv[5])},stoi(argv[6]),stod(argv[7])));auto c=continuous_mec(s);cout<<setprecision(15)<<"{\"radius_lower\":"<<c.lo<<",\"radius_upper\":"<<c.hi<<",\"center\":["<<c.c.x<<","<<c.c.y<<"],\"dmax\":"<<(s.points.empty()?0:norm(farthest(s,{stod(argv[4]),stod(argv[5])})-P{stod(argv[4]),stod(argv[5])}))<<"}";}
}

int main(int argc,char**argv){
 SCENARIO_A=0;SCENARIO_BETA=0;TARGET_CENTER={0,0};ZC=normalizer();
 P q={813.824371479152,521.018510869701};string mode=argv[1];
 cout<<setprecision(16);
 if(mode=="eval"){trial_header();trial_evaluate(q,6,128);}
 else if(mode=="cuts"){TrialEvaluator e{q,settings(5),128};auto t=e.breaks();cout<<"[";for(size_t i=0;i<t.size();i++)cout<<(i?",":"")<<t[i];cout<<"]";}
 else if(mode=="profile"){
  cout<<"theta_rad,theta_deg,pdf_rad,pdf_deg,rho_lower,rho_upper,center_x,center_y,dmax\n";
  double t;while(cin>>t){auto v=feedback(q,1,t);auto sh=boundary(v);double m=mass(v,sh,q,1,20,28)/(2*A*ZC);
   cout<<t<<","<<t*180/PI<<","<<m<<","<<m*PI/180;
   if(sh.points.empty())cout<<",nan,nan,nan,nan,nan\n";
   else{auto c=continuous_mec(sh);cout<<","<<c.lo<<","<<c.hi<<","<<c.c.x<<","<<c.c.y<<","<<norm(farthest(sh,q)-q)<<"\n";}
  }
 }
 else if(mode=="geometry"){
  double t=stod(argv[2])*PI/180;auto v=feedback(q,1,t);auto s=boundary(v);auto c=continuous_mec(s);
  cout<<"{\"theta_deg\":"<<stod(argv[2])<<",\"radius_lower\":"<<c.lo<<",\"radius_upper\":"<<c.hi<<",\"dmax\":"<<norm(farthest(s,q)-q)<<",\"center\":["<<c.c.x<<","<<c.c.y<<"],\"points\":[";
  for(size_t i=0;i<s.points.size();i++){if(i)cout<<",";cout<<"["<<s.points[i].x<<","<<s.points[i].y<<"]";}
  cout<<"],\"arcs\":[";for(size_t i=0;i<s.arcs.size();i++){auto a=s.arcs[i];if(i)cout<<",";cout<<"["<<a.o.x<<","<<a.o.y<<","<<a.r<<","<<a.l<<","<<a.h<<"]";}cout<<"]}";
 }
 else if(mode=="normalizer")cout<<ZC;
 return 0;
}
