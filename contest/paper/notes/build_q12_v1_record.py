"""Produce review tables, BibTeX, input hashes and handoff manifests from sources.

No new experiments, no simulator calls, no commits or remote writes.
"""
from pathlib import Path
import csv,json,hashlib,subprocess,shutil
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[3]
NOTES=ROOT/'contest/paper/notes'
LIT=ROOT/'正式题目工作区/参考论文/B题'
Q1=ROOT/'contest/q1/models/m01-bounded-bearing'
Q2=ROOT/'contest/q2/models/m01-reception-minimax'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readrows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def main():
    refs=json.loads((LIT/'文献清单.json').read_text(encoding='utf-8'))
    keys={1:'Tokekar2013',2:'Gholami2015',3:'VanderHook2014',4:'Yao2024',6:'Sheng2016',7:'Bai2009',11:'Welzl1991'}
    pages={1:[1,2,3],2:[2,3,4],3:[1,3,4],4:[3,4,5,6],6:[1,8],7:[6],11:[1,3]}
    entries=[];bib=[]
    for r in refs:
        rank=r['rank']
        if rank not in keys:continue
        p=LIT/r['pdf'];digest=sha(p)
        assert digest==r['sha256'],f'Original PDF hash mismatch: {p}'
        entries.append(dict(key=keys[rank],rank=rank,title=r['title'],path=str(p.relative_to(ROOT)),sha256=digest,
          source_url=r['source_url'],doi=r.get('doi'),read_pdf_pages=pages[rank],original_sha256_matches=True))
        typ='inproceedings' if rank in [1,2] else 'incollection' if rank==11 else 'article'
        field='booktitle' if typ!='article' else 'journal'
        fields={'title':r['title'],'author':r['authors'].replace(';',' and'),'year':r['year'][:4],field:r['venue'],'url':r['source_url']}
        if r.get('doi'):fields['doi']=r['doi']
        bib.append('@'+typ+'{'+keys[rank]+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields.items())+'\n}\n')
    bibpath=ROOT/'contest/paper/bibliography/q12-v1.bib';bibpath.write_text('\n'.join(bib),encoding='utf-8')
    source_dir=ROOT.parents[1]/'26problems/B题'
    dest_dir=ROOT/'contest/global/problem/B-v1'
    official=[]
    for rel in ['B题.pdf','附件/附件1.docx','附件/附件2.docx']:
        source=source_dir/rel;dest=dest_dir/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert sha(dest)==sha(source)
        else:shutil.copyfile(source,dest)
        official.append(dict(path=str(dest.relative_to(ROOT)),original_path=str(source),sha256=sha(dest)))
    provenance=dict(utc=datetime.now(timezone.utc).isoformat(),repository='https://github.com/StevenKaiyi/cumcm-2026-team',
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      literature=entries,official_local_inputs=official,
      previous_analysis=dict(path=str((LIT/'B题论文逐篇分析与策略映射.md').relative_to(ROOT)),sha256=sha(LIT/'B题论文逐篇分析与策略映射.md')),
      note='Supplied local problem version; original PDFs and DOCX remain unchanged; no online contest clarification inferred')
    (NOTES/'q12-v1-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')

    selected=readrows(Q2/'runs/R002/selected_points.csv');baselines=readrows(Q2/'runs/R002/baselines.csv')
    rows=['| B 米 | a 米 | b 米 | U 米 | 场景最大半径 米 | 移动加检测 秒 | 45°基线 U 米 |',
          '|---:|---:|---:|---:|---:|---:|---:|']
    for r in selected:
        f=lambda k:float(r[k])
        baseline=next(float(x['conditional_radius_upper_m']) for x in baselines if x['method']=='diagonal_45' and float(x['budget_m'])==f('budget_m'))
        rows.append(f"| {f('budget_m'):.0f} | {f('a_m'):.3f} | {f('b_m'):.3f} | {f('radius_upper_m'):.3f} | {f('sample_max_radius_m'):.3f} | {f('movement_and_measure_s'):.0f} | {baseline:.3f} |")
    generated='# 前两问第一版数值表\n\n由 `build_q12_v1_record.py` 从Q2-R002原始CSV自动生成。U是连续读数外包上界；场景最大值只对应指定合成工况。所有点为(0,0)首次测得0°时的示例，上下镜像等价。\n\n'+'\n'.join(rows)+'\n'
    tablepath=ROOT/'contest/paper/tables/q12-v1-results.md';tablepath.write_text(generated,encoding='utf-8')
    # Render the same generated table in the model document between explicit markers.
    form=Q2/'formulations/v01.md';text=form.read_text(encoding='utf-8')
    start='<!-- Q2_RESULTS_START -->';end='<!-- Q2_RESULTS_END -->'
    if start in text:
        text=text[:text.index(start)+len(start)]+'\n\n'+'\n'.join(rows)+'\n\n'+text[text.index(end):]
        form.write_text(text,encoding='utf-8')

    runs=[Q1/'runs/R002',Q1/'runs/R003',Q2/'runs/R001',Q2/'runs/R002',Q2/'verification/V02',Q2/'verification/V03']
    for run in runs:
        # JSON is a valid YAML subset. Mirror generated metadata, never hand edit.
        p=run/'manifest.yaml'
        payload='# Generated from manifest.json; JSON is valid YAML.\n'+(run/'manifest.json').read_text(encoding='utf-8')+'\n'
        if p.exists():assert p.read_text(encoding='utf-8')==payload
        else:p.write_text(payload,encoding='utf-8')
    results=[]
    for p in [Q1/'runs/R003/manifest.json',Q1/'runs/R003/verification.json',Q2/'runs/R002/manifest.json',Q2/'runs/R002/verification.json',Q2/'runs/R002/selected_points.csv',Q2/'verification/V02/result.json',Q2/'verification/V03/results.json',tablepath,bibpath]:
        results.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
    (NOTES/'q12-v1-result-index.json').write_text(json.dumps({'status':'verified_recommendation_not_team_adopted','files':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'verified_literature_pdfs':len(entries),'original_inputs':len(official),'selected_points':len(selected)},ensure_ascii=False))


if __name__=='__main__':main()
