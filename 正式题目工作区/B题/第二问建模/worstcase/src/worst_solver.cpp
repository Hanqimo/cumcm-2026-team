// Strict worst-feedback evaluator for S1=(0,0), theta1=0.
// Reuse the preserved continuous arc geometry, without using probability weights.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wreturn-type"
#define main preserved_expected_main
#include "../../src/solver.cpp"
#undef main
#pragma clang diagnostic pop
#include <queue>

// Include feasible isolated intersections: the expected-value implementation only
// needs positive-area boundaries, whereas minimax must also cover tangencies.
Shape strict_boundary(const Region& v) {
    Shape s=boundary(v);
    for(size_t i=0;i<v.size();++i) for(size_t j=0;j<i;++j)
        for(P p:intersect(v[i],v[j])) if(feasible(v,p,1e-8)) {
            bool seen=false;for(P x:s.points)if(norm(x-p)<1e-8)seen=true;
            if(!seen)s.points.push_back(p);
        }
    return s;
}
Region normal_interval(P q,double mid,double half,bool inner=false) {
    Region v=base();
    if(inner) v[1].r=5+1e-7; // actual normal first observations, not an excluded point
    circle(v,q,1500);circle(v,q,inner?5+1e-7:5,-1);
    double width=A+half;
    if(width<PI/2-1e-12) {
        P lo=unit(mid-width),hi=unit(mid+width);
        P n1={lo.y,-lo.x},n2={-hi.y,hi.x};
        line(v,n1,dot(n1,q));line(v,n2,dot(n2,q));
    } // dropping the wedge is a valid enclosing set for wider intervals
    return v;
}
struct Loss {double lo=0,hi=0,dmax=0;P c;bool nonempty=false;};
Loss normal_at(P q,double theta,bool inner=false,double half=0) {
    Region v=normal_interval(q,theta,half,inner);Shape s=strict_boundary(v);
    if(s.points.empty())return{};
    double dm=norm(farthest(s,q)-q);
    if(dm<=20-1e-8)return{0,0,dm,{},true};
    auto c=continuous_mec(s,2e-8);
    return{max(0.,c.lo-2e-7),c.hi+2e-7,dm,c.c,true};
}
Loss no_signal(P q) {
    // The closed region can contain a spurious nonempty boundary when N is
    // impossible. Verify strict existence before constructing its closure.
    if(safe_margin(q)>=-1e-9)return{};
    auto v=feedback(q,2);auto s=strict_boundary(v);
    if(s.points.empty())return{};
    auto c=continuous_mec(s,2e-8);
    return{max(0.,c.lo-2e-7),c.hi+2e-7,norm(farthest(s,q)-q),c.c,true};
}
struct Worst {P q;double lo=0,hi=0,normal=0,nloss=0,theta=0,safe=0;int calls=0,intervals=0;bool certified=false;};
Worst sampled(P q,int n=8) {
    Worst w;w.q=q;w.safe=safe_margin(q);auto ns=no_signal(q);w.nloss=ns.hi;
    w.lo=ns.lo;w.hi=ns.hi;auto ts=feedback_breaks(q);
    auto at=[&](double t){auto l=normal_at(q,t,true);++w.calls;if(l.lo>w.normal){w.normal=l.lo;w.theta=pos(t);}w.lo=max(w.lo,l.lo);return l.lo;};
    // Refine every detected local maximum; critical boundaries are included.
    for(size_t i=0;i+1<ts.size();++i) {
        double l=ts[i],h=ts[i+1];if(h-l<1e-12)continue;
        vector<double> val(n+1);for(int j=0;j<=n;++j)val[j]=at(l+(h-l)*j/n);
        for(int j=1;j<n;++j) if(val[j]>=val[j-1]&&val[j]>=val[j+1]&&val[j]>0) {
            double a=l+(h-l)*(j-1)/n,b=l+(h-l)*(j+1)/n;
            double x=b-(b-a)*.6180339887498949,y=a+(b-a)*.6180339887498949;
            double fx=at(x),fy=at(y);
            for(int k=0;k<30;++k){if(fx<fy){a=x;x=y;fx=fy;y=a+(b-a)*.6180339887498949;fy=at(y);}else{b=y;y=x;fy=fx;x=b-(b-a)*.6180339887498949;fx=at(x);}}
        }
    }
    w.hi=1500;return w; // sampled maximum is a lower bound, never a certificate
}
struct Interval {double lo,hi,upper;bool operator<(const Interval& b)const{return upper<b.upper;}};
Worst certified(P q,double eps,int maxcalls=300000) {
    Worst w=sampled(q,12);auto ns=no_signal(q);double fixedUpper=ns.hi;
    priority_queue<Interval> queue;auto ts=feedback_breaks(q);
    auto add=[&](double l,double h) {
        if(h-l<1e-14)return;
        double mid=(l+h)/2;auto point=normal_at(q,mid,true);++w.calls;
        if(point.lo>w.normal){w.normal=point.lo;w.theta=pos(mid);}w.lo=max(w.lo,point.lo);
        auto enclosure=normal_at(q,mid,false,(h-l)/2);++w.calls;
        queue.push({l,h,enclosure.hi});
    };
    for(size_t i=0;i+1<ts.size();++i)add(ts[i],ts[i+1]);
    while(!queue.empty()&&max(fixedUpper,queue.top().upper)>w.lo+eps&&w.calls<maxcalls) {
        auto p=queue.top();queue.pop();double m=(p.lo+p.hi)/2;add(p.lo,m);add(m,p.hi);++w.intervals;
    }
    w.hi=max({w.lo,fixedUpper,queue.empty()?0.:queue.top().upper});
    w.certified=w.hi-w.lo<=eps;return w;
}
// A lower bound valid for EVERY detector point in a rectangle. The rectangle
// lies in a disk of radius h about q. Construct source subsets producing one
// fixed feedback for all those detector points, then use their enclosing radius.
double cell_lower(P q,double hx,double hy) {
    const double margin=1e-5;double h=hypot(hx,hy),bound=0;
    auto accept=[&](Region v) {
        auto s=strict_boundary(v);if(s.points.empty())return;
        auto c=continuous_mec(s,2e-8);double low=max(0.,c.lo-2e-6);
        // A pair diameter >40 or far distance proves nonterminal throughout cell.
        if(low>20+margin || norm(farthest(s,q)-q)-h>20+margin)bound=max(bound,low);
    };
    if(norm(q)>1e-10) {
        Region v=base();v[1].r=5+margin;
        circle(v,q,1000+h+margin,-1);
        // d(q,g)>|g|+h follows since |g|<=1500.
        line(v,q*2,norm2(q)-3000*h-h*h-1e-2);
        accept(v);
    }
    if(1500-h-margin<=5+h+margin)return bound;
    vector<double> angles;
    for(double r:{5.,750.,1500.})for(double t:{-A,A}) {
        double phi=angle(unit(t)*r-q);
        for(double offset:{-A,0.,A})angles.push_back(phi+offset);
    }
    for(double theta:angles) {
        Region v=base();v[1].r=5+margin;
        circle(v,q,1500-h-margin);circle(v,q,5+h+margin,-1);
        P lo=unit(theta-A),hi=unit(theta+A),n1={lo.y,-lo.x},n2={-hi.y,hi.x};
        line(v,n1,dot(n1,q)-h-margin);line(v,n2,dot(n2,q)-h-margin);
        accept(v);
    }
    return bound;
}
struct Cell {P q;double hx,hy,lower;bool operator<(const Cell& b)const{return lower>b.lower;}};
void global_bound(double incumbent,double tolerance,long maxcells,string outfile) {
    priority_queue<Cell> cells;cells.push({{750,775},2250,775,0});long evaluated=1,splits=0;
    double threshold=incumbent-tolerance,pruned_min=1e99;
    auto start=chrono::steady_clock::now();
    while(!cells.empty()&&cells.top().lower<threshold&&evaluated<maxcells) {
        auto c=cells.top();cells.pop();++splits;
        bool x=c.hx>=c.hy;double hx=x?c.hx/2:c.hx,hy=x?c.hy:c.hy/2;
        for(int sign:{-1,1}) {
            P q=c.q+(x?P{sign*hx,0}:P{0,sign*hy});
            double low=max(c.lower,cell_lower(q,hx,hy));++evaluated;
            if(low>=threshold)pruned_min=min(pruned_min,low);else cells.push({q,hx,hy,low});
        }
        if(splits%10000==0)cerr<<"global cells="<<evaluated<<" active="<<cells.size()<<" lower="<<(cells.empty()?pruned_min:cells.top().lower)<<"\n";
    }
    double lower=min(pruned_min,cells.empty()?1e99:cells.top().lower);
    double seconds=chrono::duration<double>(chrono::steady_clock::now()-start).count();
    ofstream o(outfile);o<<setprecision(16)<<"{\"domain\":[-1500,3000,0,1550],\"upper_bound\":"<<incumbent<<",\"global_lower_bound\":"<<lower<<",\"gap_m\":"<<incumbent-lower<<",\"requested_gap_m\":"<<tolerance<<",\"completed\":"<<(lower>=threshold?"true":"false")<<",\"evaluated_cells\":"<<evaluated<<",\"active_cells\":"<<cells.size()<<",\"elapsed_seconds\":"<<seconds<<",\"arithmetic\":\"double with geometric safety margins; not outward-rounded interval arithmetic\"}\n";
    cout<<"global lower="<<setprecision(16)<<lower<<" upper="<<incumbent<<" cells="<<evaluated<<" seconds="<<seconds<<"\n";
}
void wheader(ostream& o){o<<"x,y,worst_lower,worst_upper,normal_lower,no_signal_upper,worst_theta,safe_margin,calls,interval_splits,angle_bound_complete\n";}
void wrow(ostream& o,Worst w){o<<setprecision(16)<<w.q.x<<","<<w.q.y<<","<<w.lo<<","<<w.hi<<","<<w.normal<<","<<w.nloss<<","<<w.theta<<","<<w.safe<<","<<w.calls<<","<<w.intervals<<","<<w.certified<<"\n";}
int main(int argc,char**argv) {
    if(argc<2)return 1;string mode=argv[1];
    if(mode=="eval"||mode=="cert") {P q={stod(argv[2]),stod(argv[3])};wheader(cout);wrow(cout,mode=="eval"?sampled(q,argc>4?stoi(argv[4]):8):certified(q,argc>4?stod(argv[4]):1e-3));}
    else if(mode=="global")global_bound(stod(argv[2]),stod(argv[3]),stol(argv[4]),argv[5]);
    else if(mode=="cell")cout<<setprecision(16)<<cell_lower({stod(argv[2]),stod(argv[3])},stod(argv[4]),stod(argv[5]))<<"\n";
    else if(mode=="batch") {ifstream in(argv[2]);ofstream out(argv[3]);int n=argc>4?stoi(argv[4]):6;wheader(out);string s;int k=0;while(getline(in,s)){replace(s.begin(),s.end(),',',' ');stringstream ss(s);P q;if(!(ss>>q.x>>q.y)||!useful(q))continue;wrow(out,sampled(q,n));if(++k%100==0){out.flush();cerr<<k<<" points\n";}}}
    else if(mode=="normal") {P q={stod(argv[2]),stod(argv[3])};double t=stod(argv[4]);auto v=normal_interval(q,t,0);auto s=strict_boundary(v);auto c=continuous_mec(s);cout<<setprecision(16)<<"{\"theta\":"<<t<<",\"radius\":"<<c.hi<<",\"center\":["<<c.c.x<<","<<c.c.y<<"],\"points\":[";for(size_t i=0;i<s.points.size();++i){if(i)cout<<",";cout<<"["<<s.points[i].x<<","<<s.points[i].y<<"]";}cout<<"],\"dmax\":"<<(s.points.empty()?0:norm(farthest(s,q)-q))<<"}\n";}
    else if(mode=="profile") {P q={stod(argv[2]),stod(argv[3])};int n=stoi(argv[4]);ofstream out(argv[5]);out<<"theta,radius_lower,radius_upper,dmax\n";auto ts=feedback_breaks(q);for(size_t i=0;i+1<ts.size();++i)for(int j=0;j<=n;++j){double t=ts[i]+(ts[i+1]-ts[i])*j/n;auto l=normal_at(q,t);if(l.nonempty)out<<setprecision(16)<<t<<","<<l.lo<<","<<l.hi<<","<<l.dmax<<"\n";}}
    else return 2;
}
