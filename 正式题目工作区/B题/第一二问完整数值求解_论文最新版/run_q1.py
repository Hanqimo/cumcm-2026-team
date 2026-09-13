"""由 JSON 观测文件求解第一问。示向度以正东为零、逆时针为正，单位为度。"""
import argparse,json
from pathlib import Path
from q1.solve import solve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--out',type=Path,help='新建 JSON 输出文件，不覆盖已有结果')
    args=parser.parse_args()
    try:
        result=solve(json.loads(args.input.read_text(encoding='utf-8')))
        text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open('x',encoding='utf-8') as f:f.write(text+'\n')
        print(text)
    except (ValueError,RuntimeError,FileExistsError) as e:parser.exit(2,f'错误：{e}\n')

if __name__=='__main__':main()
