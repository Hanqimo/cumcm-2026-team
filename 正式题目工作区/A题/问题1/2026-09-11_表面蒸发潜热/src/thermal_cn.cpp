// M02-v01 A02: finite volume + Rannacher startup + Crank-Nicolson thermal solve.
// Surface histories are linearly interpolated; all interpolation effects are refined separately.
#include "fv_core.hpp"
struct History {
 V times,values;size_t cursor=0;
 History(const std::string&file){std::ifstream f(file);std::string line;std::getline(f,line);while(std::getline(f,line)){std::replace(line.begin(),line.end(),',',' ');std::istringstream s(line);double t,c;if(s>>t>>c){times.push_back(t);values.push_back(c);}}
 if(times.size()<2||times.front()!=0||times.back()<1800)throw std::runtime_error("invalid surface history");
 for(size_t i=1;i<times.size();i++)if(!(times[i]>times[i-1]))throw std::runtime_error("history times not increasing");}
 double get(double t){while(cursor+2<times.size()&&times[cursor+1]<t)cursor++;double z=(t-times[cursor])/(times[cursor+1]-times[cursor]);return values[cursor]*(1-z)+values[cursor+1]*z;}
};
int main(int argc,char**argv){try{
 if(argc!=10)throw std::runtime_error("thermal env.csv surface.csv prefix N denominator lambda mode end budget");
 Env env(argv[1]);History hist(argv[2]);std::string pref=argv[3],mode=argv[7];int n=std::stoi(argv[4]);double base=1./std::stod(argv[5]),lambda=std::stod(argv[6]),end=std::stod(argv[8]),budget=std::stod(argv[9]);
 if(n<20||n%20||base<=0)throw std::runtime_error("invalid grid");
 constexpr double rhoD=820/3.55,lvA=2500900,lvB=2370;Grid q(n);V T(n+1,28),T0=T,mu(n+1),g(n),zero(n+1),source(n+1),source0(n+1),gTheta(n);Linear mat(n),mat0(n);
 for(int i=0;i<n;i++)g[i]=(i+.5)*K;
 const double fixedJ=.0002,heTest=H-lambda*lvB*fixedJ,muRoot=root(heTest*R/K);
 if(mode=="bessel")for(int i=0;i<=n;i++)T[i]=28+5*::j0(muRoot*q.r[i]/R);
 double t=0,prevdt=-1,prevtheta=-1,maxlinear=0,maxres=0,maxheat=0,minT=28,maxT=28,minTime=0,minRad=0,maxexact=0,minhe=H;
 long long steps=0;long double balance=0,convTotal=0,latentTotal=0,massFromInterpolated=0;
 auto start=std::chrono::steady_clock::now();
 std::ofstream out(pref+"_samples.csv"),dg(pref+"_diagnostics.csv");out<<std::setprecision(17)<<"time_s";for(auto field:{"T","T0"})for(int j=0;j<=20;j++)out<<","<<field<<"_"<<j;out<<"\n";
 dg<<std::setprecision(17)<<"time_s,j_water_kg_m2_s,T_surface_C,latent_W_m2,convective_W_m2,mean_T_C,mean_T0_C,cum_conv_J,cum_latent_J,energy_balance_J,max_linear_backward_error,max_scaled_residual\n";
 auto emit=[&](double j,double te){out<<t;for(const auto*v:{&T,&T0})for(int j=0;j<=20;j++)out<<","<<(*v)[j*n/20];out<<"\n";long double mean=0,mean0=0;for(int i=0;i<=n;i++){mean+=q.w[i]*T[i];mean0+=q.w[i]*T0[i];}const double geom=2*std::acos(-1)*.25;dg<<t<<","<<j<<","<<T[n]<<","<<lambda*(lvA-lvB*T[n])*j<<","<<H*(te-T[n])<<","<<double(mean/(R*R/2))<<","<<double(mean0/(R*R/2))<<","<<double(convTotal*geom)<<","<<double(latentTotal*geom)<<","<<double(balance*geom)<<","<<maxlinear<<","<<maxres<<"\n";};
 double initialJ=mode=="real"?rhoD*HM*(2.55-env.C[0]):fixedJ;emit(initialJ,mode=="real"?28:28+(lvA-lvB*28)*lambda*fixedJ/H);
 bool complete=true;std::string reason;
 while(t<end-1e-12){
 if(std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>budget){complete=false;reason="wall_budget";break;}
 double theta=steps<2?1.:.5;
 double dt=std::min({steps<2?base/2:scheduled(t,base,1),end-t,std::floor(t+1e-10)+1-t});double tn=t+dt;
 double te=env.get(env.T,tn),ce=env.get(env.C,tn),j=rhoD*HM*(hist.get(tn)-ce);
 if(mode!="real"){j=fixedJ;te=28+lambda*(lvA-lvB*28)*j/H;}
 double teOld=env.get(env.T,t),ceOld=env.get(env.C,t);
 // History cursor advances only for new times: recover old j from retained step value.
 double jOld=initialJ;
 if(mode!="real")teOld=28+lambda*(lvA-lvB*28)*fixedJ/H;
 double heOld=H-lambda*lvB*jOld,forcingOld=H*teOld-lambda*lvA*jOld;
 double he=H-lambda*lvB*j,forcing=H*te-lambda*lvA*j;
 if(he<=0||j<0)throw std::runtime_error("invalid effective boundary or evaporation direction");minhe=std::min(minhe,he);
 if(dt!=prevdt||theta!=prevtheta){for(int i=0;i<=n;i++)mu[i]=B*q.w[i]/dt;for(int i=0;i<n;i++)gTheta[i]=theta*g[i];mat.factor(gTheta,mu,theta*H);mat0.factor(gTheta,mu,theta*H);prevdt=dt;prevtheta=theta;}
 // Only the last elimination pivot changes with j; all preceding pivots are unchanged.
 mat.diag[n]=mu[n]+gTheta[n-1]+R*theta*he;double pivot=mat.diag[n]+gTheta[n-1]*mat.cp[n-1];if(!(pivot>0))throw std::runtime_error("invalid thermal pivot");mat.inv[n]=1/pivot;
 for(int i=0;i<=n;i++){
 double rhs=0,rhs0=0;
 if(i){rhs+=g[i-1]*(T[i-1]-T[i]);rhs0+=g[i-1]*(T0[i-1]-T0[i]);}
 if(i<n){rhs+=g[i]*(T[i+1]-T[i]);rhs0+=g[i]*(T0[i+1]-T0[i]);}
 else{rhs+=R*(forcingOld-heOld*T[i]);rhs0+=R*H*(teOld-T0[i]);}
 source[i]=(1-theta)*rhs;source0[i]=(1-theta)*rhs0;
 }
 mat.solve(gTheta,mu,T,theta*he,forcing/he,source);mat0.solve(gTheta,mu,T0,theta*H,te,source0);
 maxlinear=std::max({maxlinear,mat.linear_error(gTheta),mat0.linear_error(gTheta)});
 long double energy=0;double low=std::min(*std::min_element(T.begin(),T.end()),forcing/he),high=std::max(*std::max_element(T.begin(),T.end()),forcing/he);
 for(int i=0;i<=n;i++){
 double u=mat.out[i];if(!std::isfinite(u))throw std::runtime_error("nonfinite temperature");
 if(mode=="real"&&(u<0||u>50))throw std::runtime_error("temperature outside liquid-water property range [0,50] C");
 energy+=(long double)B*q.w[i]*(u-T[i]);double residual=mu[i]*(u-T[i])-source[i];if(i)residual+=theta*g[i-1]*(u-mat.out[i-1]);if(i<n)residual-=theta*g[i]*(mat.out[i+1]-u);else residual-=theta*R*(H*(te-u)-lambda*(lvA-lvB*u)*j);
 maxres=std::max(maxres,std::abs(residual)/mat.diag[i]);
 if(u<minT){minT=u;minTime=tn;minRad=q.r[i];}maxT=std::max(maxT,u);
 }
 long double hc=(long double)dt*R*H*(theta*(te-mat.out[n])+(1-theta)*(teOld-T[n])),hl=(long double)dt*R*lambda*(theta*(lvA-lvB*mat.out[n])*j+(1-theta)*(lvA-lvB*T[n])*jOld);long double b=energy-hc+hl;
 maxheat=std::max(maxheat,std::abs(double(b)));balance+=b;convTotal+=hc;latentTotal+=hl;massFromInterpolated+=(long double)dt*R*(theta*j+(1-theta)*jOld);initialJ=j;
 T=mat.out;T0=mat0.out;t=tn;steps++;
 if(std::abs(t-std::round(t))<1e-10){if(mode=="bessel")for(int i=0;i<=n;i++)maxexact=std::max(maxexact,std::abs(T[i]-(28+5*::j0(muRoot*q.r[i]/R)*std::exp(-K/B*muRoot*muRoot*t/(R*R)))));emit(j,te);}
 }
 std::ofstream full(pref+"_final.csv");full<<std::setprecision(17)<<"r_m,T_C,T0_C\n";for(int i=0;i<=n;i++)full<<q.r[i]<<","<<T[i]<<","<<T0[i]<<"\n";
 std::ofstream js(pref+"_stats.json");js<<std::setprecision(17)<<"{\"time_method\":\"Rannacher-Crank-Nicolson\",\"completed\":"<<(complete?"true":"false")<<",\"reason\":\""<<reason<<"\",\"N\":"<<n<<",\"base_dt\":"<<base<<",\"lambda\":"<<lambda<<",\"steps\":"<<steps<<",\"end_time\":"<<t<<",\"min_T\":"<<minT<<",\"min_time_s\":"<<minTime<<",\"min_radius_m\":"<<minRad<<",\"max_T\":"<<maxT<<",\"min_effective_h\":"<<minhe<<",\"max_linear_backward_error\":"<<maxlinear<<",\"max_scaled_original_residual\":"<<maxres<<",\"max_heat_balance_per_2piL\":"<<maxheat<<",\"sum_heat_balance_per_2piL\":"<<double(balance)<<",\"integral_water_per_2piL\":"<<double(massFromInterpolated)<<",\"exact_max_error\":"<<maxexact<<",\"wall_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
 if(maxlinear>1e-12||maxres>1e-9)throw std::runtime_error("thermal residual threshold");return complete?0:3;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 2;}}
