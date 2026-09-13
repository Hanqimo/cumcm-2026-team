from pathlib import Path
import json,hashlib,re,datetime,shutil,difflib
ROOT=Path(__file__).resolve().parents[1];repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());model=ROOT.parent
manifest=json.loads((ROOT/'inputs/manifest.json').read_text());archive=repo/manifest['archive']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,h in manifest['source_files'].items():assert sha(repo/rel)==h,rel
experiment=repo/'正式题目工作区/B题/第二问建模/期望损失与免补测概率_20260913'
frozen=json.loads((experiment/'manifest_final.json').read_text())
for rel,h in frozen['files'].items():assert sha(experiment/rel)==h,rel
for rel,h in manifest['pre_edit_hashes'].items():assert sha(archive/rel)==h,rel
old=(ROOT/'inputs/paper_before_figures.tex').read_text();new=(repo/'templates/论文模版.tex').read_text();mirror=(repo/'梳理/论文初稿.tex').read_text();body=(model/'第二问正文.tex').read_text()
start=new.index('\\section{问题二的模型与求解}');end=new.index('\\section{问题三的模型与求解}',start)
assert new==mirror and new[start:end].strip()==body.strip()
assert new[end:]==old[old.index('\\section{问题三的模型与求解}'):]
assert re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',new,re.S)==re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',old,re.S)
labels=re.findall(r'\\label\{([^}]+)\}',new);assert len(labels)==len(set(labels))
assert not re.search(r'\\(?:mathcal|mathscr|mathfrak|varphi|vartheta|varrho)\b',new)
assert not re.search(r'[：:]\s*\\begin\{(?:equation|align)',new)
(ROOT/'verification/paper_changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='修改前论文模版.tex',tofile='加入三张图后论文模版.tex')))
# Keep obsolete render separately, not beside the current five-page model proof.
stale=ROOT/'verification/第二问模型_page_6.png'
if stale.exists():shutil.move(stale,ROOT/'history/独立模型浮动布局调整前_page_6.png')
p=model/'README.md';s=p.read_text();s=s.replace('本次没有重新计算、增加图表或开展先验敏感性研究。','候选点优化沿用已有计算；三张论文插图及固定点反馈剖面的补算见下方“论文插图”。尚未开展先验敏感性研究。')
section='''## 论文插图

2026-09-13，新增三张中文插图：首次观测后的概率更新、第二次反馈与完成条件、权重变化下的候选点及指标权衡。图内不设总标题，s1 使用普通圆点；图名与算例条件放在 LaTeX caption 中。图件、冻结数据、代码与核查保存在[论文插图_20260913](论文插图_20260913/README.md)，三张图均提供 PDF、SVG、600 dpi PNG。

当前完整论文为15页，独立问题二模型为5页。两份全文逐字一致，独立正文与全文问题二一致。候选点没有重新优化；为第二张图在原有 w=0.5 选点补算了反馈剖面与两个区域，并通过概率归一化、角度单位转换和独立几何核查。

'''
if '## 论文插图' not in s:s=s.replace('## 历史版本',section+'## 历史版本')
p.write_text(s)
record=model/'核查记录.md';s=record.read_text();s+='''

## 2026-09-13 三张中文论文插图

遵循 scientific-visualization v1.2 的数据、配色及导出流程，在“论文插图_20260913”保存三张图及数据、代码与技能快照。原实验的全部56项清单文件哈希保持一致；改图前归档位于 templates/修订记录/20260913_122054_问题二三张插图。以修改前最新的论文模版为基准插图，保留用户同步修改的文字，再同步论文初稿和独立问题二正文。模型行间公式未改动。

绘图采用实际模型输出，图名放在 LaTeX caption 中，s1 标为圆点，无星形标记。首次后验图按距离与相对角度展开，但颜色仍为单位面积密度。反馈图使用 w=0.5 的既有选点，密度从每弧度转换为每度；270度和300度两个剩余区域半径分别为16.8723米、30.4273米，独立射线与支撑圆检查通过。候选图保留11个权重的两支镜像结果，不填充两支之间的空白。

三份 LaTeX 均编译通过，无未定义引用、缺字及 Overfull/Underfull 警告；全文15页，独立模型5页。已人工查看论文第9至12页、独立模型插图页、图件PDF实际渲染和灰度预览，两份全文插图页像素一致。图件文字均在画布内，PDF字体均已嵌入。科学计算的具体精度、元数据和来源记录见论文插图_20260913/verification。候选点的连续全局最优性仍没有证明。
''';record.write_text(s)
p=model/'核查结果.json';prior=json.loads(p.read_text());page_info=json.loads((ROOT/'verification/pdf_pages.json').read_text())
logs=[repo/'templates/论文模版.log',repo/'梳理/论文初稿.log',model/'build/第二问模型.log']
assert all(not re.search(r'Overfull|Underfull|LaTeX Warning|Missing character|undefined|^!',x.read_text(),re.M) for x in logs)
figure_files=[ROOT/f'figures/{n}.{e}' for n in ['q2_posterior','q2_feedback','q2_candidates'] for e in ['pdf','png','svg']]
tracked=[repo/x for x in ['templates/论文模版.tex','templates/论文模版.pdf','梳理/论文初稿.tex','梳理/论文初稿.pdf']]+[model/x for x in ['第二问正文.tex','第二问模型.tex','第二问模型.pdf','README.md','核查记录.md','候选区域模型说明.md']]+figure_files
result={'version':'Q2-paper-three-figures-20260913','updated_at':datetime.datetime.now().isoformat(),'adopted_model':prior['adopted_model'],'previous_check_records':str((archive/'正式题目工作区/B题/第二问建模/论文定稿版/核查结果.json').relative_to(repo)),'figure_directory':str(ROOT.relative_to(repo)),'files':{str(x.relative_to(repo)):sha(x) for x in tracked},'checks':{'full_papers_identical':True,'body_matches_paper':True,'all_display_equations_unchanged':True,'q3_and_later_unchanged':True,'no_duplicate_labels':True,'no_unwanted_fonts':True,'clean_compilation':True,'paper_pages':15,'draft_pages':15,'model_pages':5,'paper_figure_pages':[10,12],'model_figure_pages':[3,5],'archive_files_verified':len(manifest['pre_edit_hashes']),'experiment_files_verified':len(frozen['files']),'pdf_fonts_embedded':True,'all_figure_data_ranges_visible':True,'Chinese_labels_and_units_checked':True,'visual_review':'paper pages 9-12, model figure pages, PDF figure renders, grayscale; no clipping or overlap','main_and_draft_figure_pages_pixel_identical':True},'numerical_evidence':prior['numerical_evidence'],'notation':prior['notation'],'new_optimization_run':False,'new_fixed_point_profiles':True,'new_figures_generated':3,'scope':'New figure assets and captions plus short linking text; frozen candidate data retained, fixed-point profile and two regions computed for plotting.'}
p.write_text(json.dumps(result,ensure_ascii=False,indent=2))
(ROOT/'verification/final_checks.json').write_text(json.dumps(result['checks'],ensure_ascii=False,indent=2))
# A local build binary is regenerated from source; keep it outside routine Git additions.
(ROOT/'.gitignore').write_text('/src/figure_kernel\n')
files={str(f.relative_to(ROOT)):sha(f) for f in ROOT.rglob('*') if f.is_file() and f.name!='manifest_final.json' and '__pycache__' not in f.parts and f!=ROOT/'src/figure_kernel'}
(ROOT/'manifest_final.json').write_text(json.dumps({'created_at':datetime.datetime.now().isoformat(),'source_model_case':'a=0,beta=0','figure_count':3,'files':files,'paper_outputs':result['files'],'new_optimization_run':False,'independent_geometry_checks':2,'scope_limits':'Illustrations of one prior-conditioned baseline case; no continuous global optimum certificate.'},ensure_ascii=False,indent=2))
print(json.dumps(result['checks'],ensure_ascii=False,indent=2))
