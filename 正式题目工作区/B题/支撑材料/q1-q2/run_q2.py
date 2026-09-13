"""问题二入口；默认 q 和正常反馈示向度均在题目原坐标系中输入。"""
import argparse,json,sys
from pathlib import Path
from q2.api import initial_geometry,evaluate,feedback_geometry
from q2.search import run,WEIGHTS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['solve','info','evaluate','geometry'])
    parser.add_argument('--a',type=float,default=0,help='首次检测点 (a,0)，单位 m')
    parser.add_argument('--beta',type=float,default=0,help='首次示向度，逆时针角度制')
    parser.add_argument('--weights',nargs='+',type=float,default=WEIGHTS,help='solve 使用的权重列表')
    parser.add_argument('--w',type=float,default=.5,help='evaluate 使用的单个权重')
    parser.add_argument('--q',nargs=2,type=float,metavar=('X','Y'))
    parser.add_argument('--frame',choices=['global','internal'],default='global')
    parser.add_argument('--level',type=int,choices=range(7),default=6)
    parser.add_argument('--scan',type=int,default=128)
    parser.add_argument('--kind',choices=['H','N','normal'],default='normal')
    parser.add_argument('--theta',type=float,default=0,help='第二次正常示向度，角度制')
    parser.add_argument('--out',type=Path,help='solve: 新建输出文件夹；其余模式: JSON 文件路径')
    args=parser.parse_args()
    try:
        if args.mode=='solve':
            if args.out is None:parser.error('solve 需要 --out 指定一个尚不存在的文件夹')
            result=run(args.a,args.beta,args.out,args.weights)
            print('结果已保存到',args.out.resolve());return
        if args.mode=='info':result=initial_geometry(args.a,args.beta)
        else:
            if args.q is None:parser.error('evaluate / geometry 需要 --q X Y')
            if args.mode=='evaluate':result=evaluate(args.a,args.beta,args.q,args.w,args.level,args.scan,args.frame)
            else:result=feedback_geometry(args.a,args.beta,args.q,args.kind,args.theta,args.frame)
        text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x') as f:f.write(text+'\n')
        print(text)
    except (ValueError,RuntimeError,FileExistsError) as e:parser.exit(2,f'错误：{e}\n')

if __name__=='__main__':main()
