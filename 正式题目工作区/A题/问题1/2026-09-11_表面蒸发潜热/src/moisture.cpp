#include "fv_core.hpp"
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
 auto start=std::chrono::steady_clock::now();std::ofstream out(prefix+"_samples.csv"),diag(prefix+"_diagnostics.csv"),surface(prefix+"_surface.csv");
 surface<<std::setprecision(17)<<"time_s,C_surface\n0,2.55\n";
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
  T=thermal.out;C.swap(candC);t=tn;surface<<t<<","<<C[n]<<"\n";steps++;totalit+=sd.iterations;maxiter=std::max(maxiter,sd.iterations);maxres=std::max(maxres,sd.residual);maxratio=std::max(maxratio,sd.ratio);maxlinear=std::max({maxlinear,sd.linear,lin});maxupdate=std::max(maxupdate,sd.update);
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
