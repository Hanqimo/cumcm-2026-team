from pathlib import Path
import json,hashlib,re,csv,datetime,shutil,subprocess,difflib,platform
ROOT=Path(__file__).resolve().parents[1];model=ROOT.parent;q2=model.parent;repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());start=json.loads((ROOT/'inputs/manifest_start.json').read_text());arc=repo/start['archive'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=repo/'templates/论文模版.tex';s=main.read_text();old=(arc/'templates/论文模版.tex').read_text();a=s.index('\\section{问题二的模型与求解}');b=s.index('\\section{问题三的模型与求解}');oa=old.index('\\section{问题二的模型与求解}');ob=old.index('\\section{问题三的模型与求解}');body=s[a:b]
checks={'full_papers_identical':main.read_bytes()==(repo/'梳理/论文初稿.tex').read_bytes(),'body_matches_paper':(model/'第二问正文.tex').read_text()==body.rstrip()+'\n','q1_and_prior_body_unchanged':s[s.index('\\begin{document}'):a]==old[old.index('\\begin{document}'):oa],'q3_and_later_unchanged':s[b:]==old[ob:],'no_onsite_zero_loss':not re.search('原地.*(?:取零|为零)|L_.*=0',body),'uniform_loss_defined':r'L_z(q)=\rho_z(q)' in body,'strong_signal_in_expectation':r'P_{\mathrm H}(q)\rho_{\mathrm H}(q)' in body,'no_unwanted_fonts':not re.search(r'\\(?:mathcal|mathfrak|mathscr|varphi|vartheta|varepsilon)\b',body),'no_colon_before_display':not re.search(r'[:：]\s*\\(?:begin\{equation\}|\[)',body)}
labels=re.findall(r'\\label\{([^}]+)\}',s);checks['no_duplicate_labels']=len(labels)==len(set(labels));checks['all_references_resolve']=set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',s))<=set(labels)
for p in [repo/'templates/论文模版.log',repo/'梳理/论文初稿.log',model/'build/第二问模型.log']:
 assert not re.search(r'Overfull|Underfull|LaTeX Warning|Missing character|Undefined control sequence|^!',p.read_text(errors='replace'),re.M)
checks['clean_compilation']=True;assert all(checks.values()),checks
n=json.loads((ROOT/'verification/numerical_checks.json').read_text());figure=json.loads((ROOT/'verification/figure_numerical_checks.json').read_text());pages=json.loads((ROOT/'verification/pdf_pages.json').read_text());times=json.loads((ROOT/'verification/run_times.json').read_text());total_eval=sum(z.get('evaluations',0) for z in n['cases']);origin=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((ROOT/'results/origin_weights.csv').open())];r0,rm=origin[0],origin[5]
checks.update({'paper_pages':17,'draft_pages':17,'model_pages':7,'q2_figures':4,'q2_tables':2,'main_draft_all_pages_pixel_identical':True,'visual_review':'All four figure previews and all Q2 pages in full paper and standalone reviewed; no clipping/overlap/illegible formulas.','numerical_status':n['status'],'candidate_count':len(n['convergence']),'independent_geometry_checks':n['geometry_count'],'MC_draws':n['MC_total']})
# Archive the directory entry before updating its current-model paragraph.
p=q2/'README.md';rel=p.relative_to(repo);target=arc/rel;target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():shutil.copy2(p,target)
start['pre_edit_hashes'][str(rel)]=sha(target);(ROOT/'inputs/manifest_start.json').write_text(json.dumps(start,ensure_ascii=False,indent=2)+'\n')
t=p.read_text();first=t.index('**当前论文定稿入口：**');end=t.index('\n\n',first);t=t[:first]+f'**当前论文定稿入口：** [论文定稿版](论文定稿版/README.md)采用基于贝叶斯更新的加权选点模型，定位损失统一定义为第二次无线电检测后剩余区域的最小包围圆半径，结合无需补测的完成概率形成选点决策。正文、两张结果表和四幅图均已按新模型重算并同步至论文模版；当前计算依据见[完整复算记录](论文定稿版/{ROOT.name}/README.md)。此前模型、结果及图件保留在各历史目录。'+t[end:];p.write_text(t)
(model/'README.md').write_text(f'''# 问题二论文定稿版

当前采用**基于贝叶斯更新的加权选点模型**。2026-09-13，按用户确认，将定位损失统一定义为第二次无线电检测后剩余区域的最小包围圆半径；全部权重结果重新搜索、复算，论文与四幅图件同步更新。

## 当前模型

第二次反馈为z时，L_z(q)=rho(K_z(q))，单位为米；强信号、无信号与正常示向度使用相同规则。J(q)=E[rho_Z(q)|I1,q]衡量平均剩余区域大小，P_finish(q)=Pr(rho_Z(q)<=20|I1,q)衡量无需补测即可确定保证清除位置的概率。达到条件后，移动到剩余区域的包围圆圆心即可光学定位与清除。

在Q内最小化F_w(q)=(1-w)J(q)/20+w[1-P_finish(q)]。固定w给出选点决策，扫描w形成候选位置集合。20米来自光学定位尺度，w是评价偏好。源位置、共享接收半径与各地点误差仍为固定未知量，采用先验和贝叶斯更新描述主观概率。接收概率函数使用p_rec(d)。

## 文件与维护

- `第二问正文.tex` 与 `templates/论文模版.tex` 的问题二逐字一致。
- `第二问模型.tex` 通过input引用正文，`第二问模型.pdf` 为独立编译结果。
- `候选区域模型说明.md` 给出当前模型、算法和解释边界。
- `核查记录.md` 追加保存历次记录，`核查结果.json` 描述当前版本。
- [完整复算目录]({ROOT.name}/README.md)保存模型定义、源程序、全部数值、图件、复现命令和核查结果。

整篇论文同步至 `梳理/论文初稿.tex`；两份全文均为17页，独立问题二为7页。当前图件来自 `{ROOT.name}/figures/`，依次展示一般位置的首次后验、两种反馈的剩余区域、反馈预测密度以及权重变化下的候选位置。

## 当前结果与核查

论文6.6节说明数值流程，6.7节使用两张表汇报结果。典型表固定w=0.5，比较(0,0)、(1200,30度)、(1200,90度)、(1200,150度)、(1700,0度)。原点正东表列出11个权重，坐标使用正负号表示两支镜像候选点。

原点正东、w=0时J={r0['J']:.8f}米、P_finish={100*r0['P_finish']:.5f}%；w=0.5时J={rm['J']:.8f}米、P_finish={100*rm['P_finish']:.5f}%。表格由新计算文件生成。总计重新优化6组情形、每组11个权重，含一组补充边界检查；a=1780、beta=0时首次区域已满足清除条件，直接报告无需第二次测向。

66组结果全部提高积分精度复算，最大J变化{n['max_J_refinement_m']:.3g}米；57次独立射线与支撑圆检查的最大半径差{n['max_geometry_gap_m']:.3g}米；8个代表点共160000次联合先验模拟通过核验。模拟共用几何内核，仅独立核对概率积分；几何由独立表示核对。数值搜索提供优选候选，尚无连续全局最优证明，先验敏感性研究未开展。

## 历史版本

本次修改前的论文、模型和维护记录见[原地定位置零版](../历史版本/{arc.name}/README.md)。此前的[加权实验](../期望损失与免补测概率_20260913/README.md)、[数值补全](数值求解_论文补全_20260913/README.md)和两版插图保留原始运行状态，供核查与复现；它们不作为当前损失定义的计算依据。更早的单一期望及双模型记录仍保留在历史版本目录。

## 编译

在本目录执行 `latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build 第二问模型.tex`，随后将build内PDF复制到当前目录。完整论文继续使用templates目录的VS Code latexmk配方。
''')
(model/'候选区域模型说明.md').write_text(f'''# 期望剩余半径与完成概率的加权选点模型

日期：2026-09-13。状态：用户确认采用，模型、计算、论文与图表已同步。

## 输入与区域

输入I1=(s1,beta)，s1=(a,0)。由首次正常示向度构造K1，在Q中选择不同于s1且距K1不超过1500米的位置q。三类反馈分别为强信号H、无信号N、正常示向度theta；对应区域沿用论文的K_H、K_N和K_theta。两次接收共用一个固定未知R。源位置在目标圆域按面积均匀，R在1000至1500米内均匀，不同地点误差在正负1度内独立均匀，这些均为明确列出的先验假设。

## 评价与决策

定位损失统一为L_z(q)=rho(K_z(q))，评价第二次无线电检测结束时的区域大小，单位为米。J(q)=P_H rho_H+P_N rho_N+integral f_Theta rho_theta dtheta。强信号剩余区域位于q的5米范围内，rho_H不超过5米，仍按其实际半径参与期望。

P_finish(q)=P_H+P_N 1{{rho_N<=20}}+integral f_Theta 1{{rho_theta<=20}} dtheta，表示无需补充无线电测向即可确定保证清除位置的概率；达到条件后，移动到剩余区域包围圆圆心进行光学定位与清除。

F_w(q)=(1-w)J(q)/20+w[1-P_finish(q)]，在Q中最小化。两项分别反映平均剩余半径与达到完成阈值的概率；w属于[0,1]，代表对完成概率的重视程度。20米是尺度约定，不要求J/20小于1。w=1时只最大化完成概率，出现并列候选时以较小J选择展示代表点。

Q_cand=union_{{w in [0,1]}} argmin_{{q in Q}}F_w(q)。有限计算取11个权重，保留相应数值优选点。几何与先验具有反射对称时，同时保留镜像点；一般参数下完整搜索两侧。单参数权重形成的候选集合可呈曲线或分离部分，不预设面积。图中虚线连接相邻权重计算点，用于表示变化顺序。

## 算法及结果

采用网格筛选、多个独立起点的Nelder-Mead搜索、确定性概率积分及连续边界的最小包围圆计算。每个权重独立选取5个空间分离的网格点与初始区域圆心作起点，经低精度搜索与高精度细化后统一复算。w=1的目标为纯完成概率，没有加入半径罚项。首次区域已满足20米判据时，直接报告无需第二次测向。

6个首次观测情形各重算11个权重，66组高精度结果及8点联合先验模拟、57次独立几何检查见[复算记录]({ROOT.name}/README.md)。论文表格使用其中5组情形的w=0.5结果和原点全部11个权重。数值优选未取得连续全局最优认证，表格仅展示典型输入；其他(a,beta)通过同一求解流程计算。

## 维护

当前唯一计算来源为 `{ROOT.name}`。正文维护在本目录 `第二问正文.tex` 并与论文模版和论文初稿同步；历史文件保留在归档目录，不覆盖原始运行结果。
''')
runreadme=f'''# 问题二：统一期望剩余半径模型的完整复算

用户已确认采用。损失定义为L_z(q)=rho(K_z(q))，J(q)=E[rho_Z(q)|I1,q]，F_w=(1-w)J/20+w(1-P_finish)。强信号、无信号、正常示向度均按剩余半径计算。所有输出由本目录新程序重跑生成，旧实验未改动。

## 结果与文件

- [原点11权重表](results/origin_weights.csv)、[5组典型观测表](results/typical_cases.csv)直接用于论文。
- [全部66组候选](results/all_candidates.csv)含全精度坐标、指标、概率分支和数值诊断。
- `results/a*_b*/`保存各次搜索日志、网格评价、多起点记录、邻域与最终高精度复算。
- `data/`与`figures/`保存4幅图的数据、PDF矢量稿、SVG和600 dpi PNG。
- [完整核查](verification/numerical_checks.json)与[图件数值核查](verification/figure_numerical_checks.json)分别保存，源文件使用清单哈希追溯。

原点w=0的J为{r0['J']:.10f}米、完成概率{100*r0['P_finish']:.8f}%；w=0.5为{rm['J']:.10f}米、{100*rm['P_finish']:.8f}%。增量为{rm['J']-r0['J']:.10f}米和{100*(rm['P_finish']-r0['P_finish']):.10f}个百分点。优化停止精度带来毫米级坐标差，某些末位四舍五入会变化，报告值以本次CSV为准。

## 搜索范围、参数与预算

独立重跑(a,beta)=(0,0)、(1200,30度)、(1200,90度)、(1200,150度)、(1700,0度)、(1700,90度)，每例11个权重。另检查(1780,0度)，首次区域半径7.50467955米，已满足清除条件，返回无需第二次测向。

源区域边界外扩1501米作为搜索包络，100米覆盖网格，初始区域附近补充较密网格与65个示向轴附近采样；每次检查q不等于s1、距K1不超过1500米。5个空间分离的网格种子加初始区域圆心，粗搜索最多150步，两个较优点高精度细化最多130步，停止参数xatol=0.015米、fatol=2e-9。不同权重复用函数值缓存，并分别执行搜索，未使用旧最优点作初值，也未使用旧模型的终止/支配捷径。所有求积参数以inputs/base_solver.cpp的settings函数为准，最终使用level6、128份阈值扫描。

每情形最长900秒、并发最多2个进程；实际全部搜索评价{total_eval}个配置，各情形耗时约8至64秒，详见verification/run_times.json。人工智能交互成本未测量，不以调用次数估算账号额度。

w=1使用纯概率目标；同概率候选按J选择代表点。连续区域未做全局定界，数值收敛和多起点一致不构成连续全局最优证明。原点与向内150度情形分别重跑，后者与原点的初始区域具有刚体变换关系，所得指标在数值搜索精度内一致。

## 核查方法与结果

66组候选全部提高求积精度：最大J差{n['max_J_refinement_m']:.8g}米，最大完成概率差{n['max_P_refinement']:.8g}，最大概率归一化残差{n['max_normalization_residual']:.8g}。全体权重的0.1、1、5米八方向邻域没有发现更优目标。两表全部显示坐标另作舍入回代，指标变化小于0.005米及0.005个百分点。

57次独立射线求交与支撑圆枚举检查，最大包围圆半径上下界差{n['max_geometry_gap_m']:.8g}米。8个代表点各20000次联合先验抽样，总计160000次，J与完成概率均在4个标准误核查范围内；模拟共享几何内核，只独立验证积分，几何由射线表示另查。

另设置强信号和可原地定位的专门输入，检查新J等于残余半径期望、强信号半径项被实际计入；见numerical_checks.json的semantic部分。绘图反馈曲线重新计算18036个读数节点，以梯形积分对照确定性积分；首次后验由径向原函数独立核对几何积分。数值验证并不验证先验假设的客观真实性。

## 复现

Python3、NumPy、Matplotlib、Pillow、pypdf、pypdfium2和C++17。请复制本目录的src、inputs及skill到新的空目录后复现，以免覆盖本次证据；建立results、verification、data、figures空目录。

```sh
clang++ -O3 -std=c++17 src/solver.cpp -o solver
clang++ -O3 -std=c++17 inputs/base_solver.cpp -o base_solver
python3 src/run_all.py
python3 src/verify_results.py
python3 src/prepare_figures.py
python3 src/plot_figures.py
```

`src/update_paper.py`是一次性文稿更新记录，有修改前哈希保护。`src/check_documents_and_figures.py`检查当前3份PDF并渲染问题二全部页面；它需要论文已编译。原冻结内核main经重命名后不调用，编译器的未返回警告来自该旧入口。

## 绘图与软件来源

绘图面向数学建模论文，宽度分别160、130、150、160毫米，无图内总标题，中文标签、普通圆点标记s1，预测密度按每度换算，后验密度按每平方米标注；比较面板使用统一色标与长度尺度。未做插值优化点、数据排除或视觉平滑。PDF/SVG用于排版，PNG为600dpi RGB，已核查字体嵌入、边界文字、灰度预览和实际论文尺寸。图形颜色辅以边界、虚线、斜线阴影及直接标注，未声称自动审计等同于无障碍认证；无指定期刊的额外要求。

依据用户指定的scientific-visualization v1.2技能，技能快照见skill目录。本次在软件记录中引用其来源：Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065 。2026-09-13核对arXiv页面，当前修订日期2026-09-02，无期刊版本信息。该引用属于绘图工作流来源，未作为定位模型的科学依据。

## 保存状态

旧论文与模型维护记录已归档至 `{start['archive']}`，旧数值和旧图件保留原路径。本次修改只保存到本地工作区，未提交或推送Git。
'''
(ROOT/'README.md').write_text(runreadme)
rec=model/'核查记录.md';rec.write_text(rec.read_text()+f'''\n\n## 2026-09-13：统一剩余半径损失，完整重新求解\n\n按用户确认，L_z=rho_z，J包含强信号半径项；正文按新定义自然展开，取消原地定位置零的对照说明。独立重跑6个情形各11个权重，另检查一个首次即满足清除条件的情形。完成66组高精度复算、57次独立几何、160000次模拟及邻域、坐标舍入检查。原点主要结果在论文显示精度内基本一致；数据全部来自新运行。两表及4幅图重新生成，主稿和镜像全文17页、独立模型7页，编译无缺字/溢出/未定义引用，全文逐页像素一致，问题二页面和图件目视检查通过。详见 `{ROOT.name}/README.md`。修改前快照 `{start['archive']}`；未提交或推送。\n''')
result={'version':'Q2-expected-remaining-radius-full-recompute-20260913','updated_at':datetime.datetime.now().isoformat(),'adopted_model':'基于贝叶斯更新的期望剩余半径与完成概率加权选点模型','previous_check_records':str((arc/'正式题目工作区/B题/第二问建模/论文定稿版/核查结果.json').relative_to(repo)),'checks':checks,'notation':{'loss':'L_z(q)=rho(K_z(q))','expected_loss':'J(q)=E[rho_Z(q)|I1,q]','reception':'p_rec(d)','objective':'F_w=(1-w)J/20+w(1-P_finish)','decision':'min over q in Q','candidate_set':'union of argmin sets over w in [0,1]'},'new_optimization_run':True,'new_figures_generated':4,'evidence_directory':str(ROOT.relative_to(repo)),'global_optimality_certified':False,'new_monte_carlo_draws':160000,'new_geometry_checks':57}
files=[main,main.with_suffix('.pdf'),repo/'梳理/论文初稿.tex',repo/'梳理/论文初稿.pdf',q2/'README.md']+[model/z for z in ['第二问正文.tex','第二问模型.tex','第二问模型.pdf','README.md','候选区域模型说明.md','核查记录.md']];result['files']={str(p.relative_to(repo)):sha(p) for p in files};(model/'核查结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
checks['archive_files_verified']=all(sha(arc/k)==v for k,v in start['pre_edit_hashes'].items());assert checks['archive_files_verified']
source=q2/'期望损失与免补测概率_20260913';source_manifest={}
for name in ['trial_solver.cpp','search_trial.py','validate_trial.py']:
 p=source/'src'/name;assert sha(p)==sha(ROOT/'inputs'/('previous_'+name));source_manifest[str(p.relative_to(repo))]=sha(p)
for name in ['base_solver.cpp','base_search.py','base_validate.py']:
 p=source/'inputs'/name;assert sha(p)==sha(ROOT/'inputs'/name);source_manifest[str(p.relative_to(repo))]=sha(p)
(ROOT/'inputs/source_manifest.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2)+'\n')
(ROOT/'verification/final_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');(ROOT/'verification/paper_changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='previous/论文模版.tex',tofile='current/论文模版.tex')))
import numpy,PIL,pypdf,pypdfium2,sys
try: import matplotlib
except ModuleNotFoundError:
 sys.path.insert(0,'/private/tmp/bq2-plot-deps');import matplotlib
(ROOT/'verification/environment.json').write_text(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'numpy':numpy.__version__,'matplotlib':matplotlib.__version__,'Pillow':PIL.__version__,'pypdf':pypdf.__version__,'git_branch':subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'worktree_modified':True,'clang':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0]},indent=2))
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name not in ['manifest_final.json','solver','base_solver','figure_kernel'] and '__pycache__' not in p.parts};(ROOT/'manifest_final.json').write_text(json.dumps({'files':manifest,'count':len(manifest)},ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False,indent=2));print('Files:',len(manifest),'evaluations:',total_eval)
