"""从观测输入重新生成论文两问的数值结果，不读取已保存候选点作为起点。"""
from pathlib import Path
import argparse,csv,json,platform,hashlib
from q1.solve import solve
from q2.search import run as solve_q2
ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True,help='新建结果目录')
    parser.add_argument('--cases',type=Path,default=ROOT/'examples/q2_cases.json')
    args=parser.parse_args();config=json.loads(args.cases.read_text())
    args.out.mkdir(parents=True,exist_ok=False)
    q1=args.out/'q1';q1.mkdir()
    for source in sorted((ROOT/'examples').glob('q1_*.json')):
        result=solve(json.loads(source.read_text()))
        (q1/source.name).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    summaries=[];rows=[]
    for case in config['cases']:
        a,b=case['a'],case['beta_deg']
        summary=solve_q2(a,b,args.out/'q2'/f'a{a:g}_b{b:g}',config['weights'])
        summaries.append(summary)
        rows.extend(dict(row,a_m=a,beta_deg=b) for row in summary['candidates'])
        (args.out/'case_summaries.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2))
    fields=['a_m','beta_deg','w','x_global','y_global','J','P_finish','F','probability_residual','mec_gap']
    tables={'all_candidates.csv':rows,
            'origin_weights.csv':[r for r in rows if r['a_m']==0 and r['beta_deg']==0],
            'typical_cases.csv':[r for r in rows if r['w']==.5]}
    for name,data in tables.items():
        with (args.out/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(data)
    manifest={'input_config':config,'python':platform.python_version(),
              'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.suffix in ('.py','.cpp','.hpp') and '__pycache__' not in p.parts},
              'no_second_detection_cases':[r['case'] for r in summaries if r.get('status')=='no_second_detection_needed'],
              'note':'重新运行搜索的坐标可能有小幅数值差异；参照表保存在 reference_results，未用于搜索。'}
    (args.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('论文算例复算完成：',args.out.resolve())

if __name__=='__main__':main()
