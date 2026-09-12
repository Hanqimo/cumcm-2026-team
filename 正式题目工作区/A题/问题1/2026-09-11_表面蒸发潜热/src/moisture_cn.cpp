#include "fv_core.hpp"
// Conservative theta method, with Picard and independently recomputed nonlinear residual.
bool stepCN(const Grid&q,const V&old,V&next,double dt,double ceOld,double ceNew,double theta,double tol,bool constant,const V&fOld,const V&fNew,StepDiag&st){
 V mu(q.n+1),g(q.n),gold(q.n),ng(q.n),gt(q.n),cur=old,source(q.n+1);
 conduct(q,old,gold,constant);g=gold;
 for(int i=0;i<=q.n;i++){
 mu[i]=q.w[i]/dt;double l=0;if(i)l+=gold[i-1]*(old[i-1]-old[i]);if(i<q.n)l+=gold[i]*(old[i+1]-old[i]);else l+=R*HM*(ceOld-old[i]);
 source[i]=(1-theta)*(l+fOld[i])+theta*fNew[i];}
 Linear a(q.n);
 for(int it=1;it<=50;it++){
 for(int i=0;i<q.n;i++)gt[i]=theta*g[i];a.factor(gt,mu,theta*HM);a.solve(gt,mu,old,theta*HM,ceNew,source);conduct(q,a.out,ng,constant);
 st.linear=std::max(st.linear,a.linear_error(gt));double res=0,upd=0,amp=0;
 for(int i=0;i<=q.n;i++){
 double F=mu[i]*(a.out[i]-old[i])-source[i];if(i)F+=theta*ng[i-1]*(a.out[i]-a.out[i-1]);if(i<q.n)F-=theta*ng[i]*(a.out[i+1]-a.out[i]);else F-=theta*R*HM*(ceNew-a.out[i]);
 double diagonal=mu[i]+theta*((i?ng[i-1]:0)+(i<q.n?ng[i]:R*HM));res=std::max(res,std::abs(F)/diagonal);upd=std::max(upd,std::abs(a.out[i]-cur[i]));amp=std::max(amp,std::abs(a.out[i]));}
 next=a.out;st.iterations=it;st.residual=res;st.update=upd;st.ratio=res/(tol*(1+amp));
 if(res<=tol*(1+amp)&&upd<=tol*(1+amp))return true;
 cur=a.out;g.swap(ng);
 }return false;
}
int main(int argc,char**argv){try{
 if(argc!=9)throw std::runtime_error("moisture_cn env prefix N denominator tolerance mode end budget");
 Env env(argv[1]);std::string pref=argv[2],mode=argv[6];int n=std::stoi(argv[3]);double base=1./std::stod(argv[4]),tol=std::stod(argv[5]),end=std::stod(argv[7]),budget=std::stod(argv[8]);Grid q(n);
 if(n<20||n%20)throw std::runtime_error("bad grid");
 V C(n+1,2.55),next(n+1),fo(n+1,0),fn(n+1,0);double eigen=root(HM*R/5e-9);
 if(mode=="bessel")for(int i=0;i<=n;i++)C[i]=1+.2*::j0(eigen*q.r[i]/R);
 if(mode=="mms")for(int i=0;i<=n;i++)C[i]=exactC(q.r[i],0);
 double t=0,cap=1e99,minC=C[n],maxC=C[0],maxres=0,maxratio=0,maxlinear=0,maxbal=0,maxexact=0;long double cumBal=0,cumBoundary=0;long long steps=0,totalit=0,rejected=0;int maxit=0;
 auto ce=[&](double t){if(mode=="equilibrium")return 2.55;if(mode=="bessel")return 1.;if(mode=="mms"){double b=.1*std::exp(-t/100),cs=1+2*b;return cs+diffus(cs)*2*b/(R*HM);}return env.get(env.C,t);};
 std::ofstream samples(pref+"_samples.csv"),surface(pref+"_surface.csv"),dg(pref+"_diagnostics.csv");samples<<std::setprecision(17)<<"time_s";for(int j=0;j<=20;j++)samples<<",C_"<<j;samples<<"\n";surface<<std::setprecision(17)<<"time_s,C_surface\n";dg<<std::setprecision(17)<<"time_s,steps,iterations,max_scaled_residual,max_ratio,max_linear_backward_error,cum_water_balance,cum_outward_water_per_rhod_2piL\n";
 auto emit=[&](){samples<<t;for(int j=0;j<=20;j++)samples<<","<<C[j*n/20];samples<<"\n";dg<<t<<","<<steps<<","<<totalit<<","<<maxres<<","<<maxratio<<","<<maxlinear<<","<<double(cumBal)<<","<<double(cumBoundary)<<"\n";};emit();surface<<0<<","<<C[n]<<"\n";
 auto start=std::chrono::steady_clock::now();bool complete=true;std::string reason;
 while(t<end-1e-12){
 if(std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>budget){complete=false;reason="wall_budget";break;}
 double theta=steps<2?1:.5,dt=std::min({steps<2?base/2:scheduled(t,base,1),cap,end-t,std::floor(t+1e-10)+1-t});
 if(dt<1e-6){complete=false;reason="minimum_dt";break;}
 double tn=t+dt,ceo=ce(t),cen=ce(tn);if(mode=="mms"){source_mms(q,t,fo);source_mms(q,tn,fn);}
 StepDiag sd;if(!stepCN(q,C,next,dt,ceo,cen,theta,tol,mode=="bessel",fo,fn,sd)){cap=dt/2;rejected++;continue;}
 long double change=0,sources=0;for(int i=0;i<=n;i++){
 if(!std::isfinite(next[i])||next[i]<=0||(mode=="real"&&next[i]>2.55+1e-8))throw std::runtime_error("moisture positivity/range");
 change+=(long double)q.w[i]*(next[i]-C[i]);sources+=(1-theta)*fo[i]+theta*fn[i];minC=std::min(minC,next[i]);maxC=std::max(maxC,next[i]);}
 long double loss=(long double)dt*R*HM*((1-theta)*(C[n]-ceo)+theta*(next[n]-cen));long double bal=change+loss-dt*sources;cumBal+=bal;cumBoundary+=loss;maxbal=std::max(maxbal,std::abs(double(bal)));
 C.swap(next);t=tn;steps++;totalit+=sd.iterations;maxit=std::max(maxit,sd.iterations);maxres=std::max(maxres,sd.residual);maxratio=std::max(maxratio,sd.ratio);maxlinear=std::max(maxlinear,sd.linear);surface<<t<<","<<C[n]<<"\n";
 if(std::abs(t-std::round(t))<1e-10){if(mode=="bessel"||mode=="mms")for(int i=0;i<=n;i++){double exact=mode=="bessel"?1+.2*::j0(eigen*q.r[i]/R)*std::exp(-5e-9*eigen*eigen*t/(R*R)):exactC(q.r[i],t);maxexact=std::max(maxexact,std::abs(C[i]-exact));}emit();}
 }
 std::ofstream full(pref+"_final.csv");full<<std::setprecision(17)<<"r_m,C_kg_kg\n";for(int i=0;i<=n;i++)full<<q.r[i]<<","<<C[i]<<"\n";
 std::ofstream js(pref+"_stats.json");js<<std::setprecision(17)<<"{\"time_method\":\"Rannacher-Crank-Nicolson\",\"completed\":"<<(complete?"true":"false")<<",\"reason\":\""<<reason<<"\",\"N\":"<<n<<",\"base_dt\":"<<base<<",\"steps\":"<<steps<<",\"end_time\":"<<t<<",\"rejected_steps\":"<<rejected<<",\"max_picard\":"<<maxit<<",\"total_picard\":"<<totalit<<",\"max_scaled_original_residual\":"<<maxres<<",\"max_residual_ratio\":"<<maxratio<<",\"max_linear_backward_error\":"<<maxlinear<<",\"min_C\":"<<minC<<",\"max_C\":"<<maxC<<",\"max_water_balance_per_rhod_2piL\":"<<maxbal<<",\"sum_water_balance_per_rhod_2piL\":"<<double(cumBal)<<",\"outward_water_per_rhod_2piL\":"<<double(cumBoundary)<<",\"exact_max_error\":"<<maxexact<<",\"wall_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
 if(maxlinear>1e-12||maxratio>1)throw std::runtime_error("residual threshold");return complete?0:3;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 2;}}
