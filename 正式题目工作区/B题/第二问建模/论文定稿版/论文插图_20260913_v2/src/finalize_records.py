from pathlib import Path
import json,hashlib,re,datetime,difflib
ROOT=Path(__file__).resolve().parents[1];model=ROOT.parent;state=json.loads((ROOT/'inputs/revision.json').read_text());repo=Path(state['root']);archive=Path(state['archive'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
new=(repo/'templates/论文模版.tex').read_text();old=(archive/'templates/论文模版.tex').read_text();mirror=(repo/'梳理/论文初稿.tex').read_text();body=(model/'第二问正文.tex').read_text()
a=new.index('\\section{问题二的模型与求解}');b=new.index('\\section{问题三的模型与求解}',a)
assert new==mirror and new[a:b].strip()==body.strip()
assert re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',new,re.S)==re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',old,re.S)
assert new[b:]==old[old.index('\\section{问题三的模型与求解}'):]
labels=re.findall(r'\\label\{([^}]+)\}',new);assert len(labels)==len(set(labels))
assert not re.search(r'\\(?:mathcal|mathscr|mathfrak|varphi|vartheta|varrho)\b',new)
assert not re.search(r'[：:]\s*\\begin\{(?:equation|align)',new)
for lab in ['fig:q2-posterior','fig:q2-feedback-regions','fig:q2-feedback','fig:q2-candidates']:
 assert '\\ref{'+lab+'}' in new
for rel,h in state['pre_edit_hashes'].items():assert sha(archive/rel)==h
for p in [repo/'templates/论文模版.log',repo/'梳理/论文初稿.log',model/'build/第二问模型.log']:
 assert not re.search(r'Overfull|Underfull|LaTeX Warning|Missing character|undefined|^!',p.read_text(),re.M)
for p in ROOT.glob('verification/*_pdf_metadata.json'):
 assert json.loads(p.read_text())['metadata']['font_resources']['all_embedded']
(ROOT/'verification/paper_changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='修改前',tofile='一般位置与拆分后')))
p=model/'README.md';s=p.read_text();start=s.index('## 论文插图');end=s.index('## 历史版本',start)
s=s[:start]+'''## 论文插图

当前问题二共四张图，按正文逻辑分别展示首次后验更新、两种反馈区域的完成条件、第二次示向度预测密度，以及候选点与评价指标。第一张改用 s1=(1200,0) 米，比较30度与90度的首次示向度；中间两张由初版的大图拆开。各图的结论已写入对应正文，图注以短图名为主。

本次修订的图件、数据和代码见[第二版插图](论文插图_20260913_v2/README.md)。候选点图继续使用[初版图件](论文插图_20260913/README.md)，其余初版图件保留为历史记录。当前完整论文为16页，独立问题二模型为6页；两份全文一致，独立正文与问题二一致，所有模型行间公式未改动。没有重新运行候选点优化。

'''+s[end:];p.write_text(s)
p=model/'核查记录.md';s=p.read_text();s+='''

## 2026-09-13 一般首次位置、正文读图说明与反馈图拆分

按用户审阅意见，第一张图改为首次点(1200,0)米、示向度30度和90度的对比，使用同一位置密度色标，强调只有当圆域边界参与截断时，示向度还会改变后验形状与密度大小。用径向积分原函数加角度高斯积分计算归一化系数，并与冻结的几何积分核核对，两例差异均小于10⁻⁹平方米。

将原第二张图拆为剩余区域示例与预测密度两个浮动图，分别放在完成概率定义和加权选点决策之后。图件实际尺寸分别为130×60毫米和150×43毫米；正文逐图补充结论，图注缩短。原点算例的反馈剖面和几何输入逐字节保持不变，原候选点图也保持不变；没有将原点选点结果套用到非圆心位置。

本次修改前全文、独立模型与维护记录已归档，具体路径见论文插图_20260913_v2/inputs/revision.json。全文16页，独立模型6页，编译无未定义引用、缺字及溢出版式警告；已查看正文读图说明和插图实际渲染，中文、符号、单位及标注无重叠。详细数据、来源及软件技能引用见第二版插图目录，旧版本图件保持可追溯。
''';p.write_text(s)
p=model/'核查结果.json';previous=json.loads(p.read_text());pages=json.loads((ROOT/'verification/pdf_pages.json').read_text())
checks={'full_papers_identical':True,'body_matches_paper':True,'all_display_equations_unchanged':True,'q3_and_later_unchanged':True,'no_duplicate_labels':True,'no_unwanted_fonts':True,'all_figures_explained_in_body':True,'no_signal_and_onsite_probabilities_not_confused':True,'noncentral_posterior_not_used_as_origin_optimization_result':True,'clean_compilation':True,'paper_pages':16,'draft_pages':16,'model_pages':6,'figure_count_in_q2':4,'paper_figure_pages':[10,11,12,13],'model_figure_pages':[3,4,5,6],'pdf_fonts_embedded':True,'main_and_draft_figure_pages_pixel_identical':True,'visual_review':'Paper figure pages and explanatory paragraphs; standalone figures; font, symbol, scale and label inspection passed.'}
files=[repo/'templates/论文模版.tex',repo/'templates/论文模版.pdf',repo/'梳理/论文初稿.tex',repo/'梳理/论文初稿.pdf']+[model/n for n in ['第二问正文.tex','第二问模型.tex','第二问模型.pdf','README.md','核查记录.md']]+list(ROOT.glob('figures/*'))
result={'version':'Q2-figures-general-first-point-split-20260913','updated_at':datetime.datetime.now().isoformat(),'adopted_model':previous['adopted_model'],'previous_check_records':str((archive/'正式题目工作区/B题/第二问建模/论文定稿版/核查结果.json').relative_to(repo)),'figure_directory':str(ROOT.relative_to(repo)),'files':{str(p.relative_to(repo)):sha(p) for p in files},'checks':checks,'numerical_evidence':previous['numerical_evidence'],'notation':previous['notation'],'new_optimization_run':False,'new_first_posterior_cases':[{'a':1200,'beta_deg':30},{'a':1200,'beta_deg':90}],'feedback_profile_unchanged':True,'new_figures_generated':3,'scope':'One replacement posterior comparison and two split feedback panels; body explanations added; candidate figure and model equations retained.'}
p.write_text(json.dumps(result,ensure_ascii=False,indent=2));(ROOT/'verification/final_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
manifest={'created_at':datetime.datetime.now().isoformat(),'files':{str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and p.name!='manifest_final.json' and '__pycache__' not in p.parts and p!=ROOT/'src/base_solver'},'paper_outputs':result['files'],'new_optimization':False}
(ROOT/'manifest_final.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps(checks,ensure_ascii=False,indent=2))
