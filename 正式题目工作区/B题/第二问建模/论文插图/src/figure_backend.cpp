#include "worst_backend.hpp"
int main(int argc,char**argv) {
    if(argc<2)return 1;string mode=argv[1];
    if(mode=="batch") {
        ifstream in(argv[2]);ofstream out(argv[3]);int level=argc>4?stoi(argv[4]):3;
        out<<"x,y,expected_radius,worst_lower,worst_upper,normal_lower,no_signal_radius,P_N,worst_calls\n";
        string s;int k=0;
        while(getline(in,s)) {
            replace(s.begin(),s.end(),',',' ');stringstream ss(s);P q;if(!(ss>>q.x>>q.y))continue;
            auto e=evaluate(q,settings(level));auto w=certified(q,.002);
            if(!w.certified){cerr<<"Unclosed angle bound\n";return 2;}
            out<<setprecision(16)<<q.x<<","<<q.y<<","<<e.rmean<<","<<w.lo<<","<<w.hi<<","<<w.normal<<","<<w.nloss<<","<<e.pn<<","<<w.calls<<"\n";
            if(++k%200==0)out.flush();
        }
    }else if(mode=="curve") {
        P e={stod(argv[2]),stod(argv[3])},w={stod(argv[4]),stod(argv[5])};ofstream out(argv[6]);
        out<<"t,x,y,expected_radius,normal_lower,no_signal_radius,worst_lower,worst_upper\n";
        vector<double> ts;for(int j=0;j<=310;j++)ts.push_back(-.25+j*.005);ts.push_back(0);ts.push_back(1);uniquev(ts);
        for(double t:ts){P q=e+(w-e)*t;auto r=certified(q,2e-5);auto avg=evaluate(q,settings(3));
            if(!r.certified)return 2;
            out<<setprecision(16)<<t<<","<<q.x<<","<<q.y<<","<<avg.rmean<<","<<r.normal<<","<<r.nloss<<","<<r.lo<<","<<r.hi<<"\n";}
    }else return 3;
    return 0;
}
