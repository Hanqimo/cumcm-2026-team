from pathlib import Path
import csv,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];model=ROOT.parent;repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());start=json.loads((ROOT/'inputs/manifest_start.json').read_text())
for rel in ['templates/论文模版.tex','梳理/论文初稿.tex','正式题目工作区/B题/第二问建模/论文定稿版/第二问正文.tex','正式题目工作区/B题/第二问建模/论文定稿版/第二问模型.tex']:
 assert hashlib.sha256((repo/rel).read_bytes()).hexdigest()==start['pre_edit_hashes'][rel],f'Concurrent change: {rel}'
s=(repo/'templates/论文模版.tex').read_text();a=s.index('\\section{问题二的模型与求解}');b=s.index('\\section{问题三的模型与求解}');body=s[a:b]
def replace(old,new):
 global body
 assert old in body,old[:100]
 body=body.replace(old,new)
replace('其中，“定位损失”用剩余可行区域的最小包围圆半径衡量尚未消除的位置不确定性；若整个区域已位于当前检测点的20米以内，能够原地完成光学精确定位，则损失取零。将各种反馈下的损失按概率求平均，就得到期望定位损失，数值越小越好。','其中，“定位损失”指第二次无线电检测后剩余可行区域的最小包围圆半径，用来衡量源位置还有多大的不确定性。将各种反馈下的半径按概率求平均，就得到期望定位损失，数值越小，表示平均定位范围越小。')
x=body.index('\\subsection{三种反馈下的定位损失}');y=body.index('\\subsection{基于贝叶斯更新的反馈预测}',x)
body=body[:x]+r'''\subsection{定位损失的定义}

第二次反馈为 \(z\) 时，将剩余区域的最小包围圆半径定义为定位损失，即 \(L_z(q)=\rho_z(q)\)，单位为米。三种反馈均按这一规则计算。

\begin{enumerate}[label=(\arabic*),leftmargin=2.2em]
  \item \textbf{强信号。} 剩余区域 \(K_{\mathrm H}(q)\) 位于检测点的5米范围内，取 \(L_{\mathrm H}(q)=\rho_{\mathrm H}(q)\le5\) 米。
  \item \textbf{无信号。} 根据未能接收信号的信息排除部分源位置，取剩余区域的半径 \(L_{\mathrm N}(q)=\rho_{\mathrm N}(q)\)。
  \item \textbf{正常示向度。} 将新读数对应的角域与已有区域相交，取更新后区域的半径 \(L_\theta(q)=\rho_\theta(q)\)。
\end{enumerate}

'''+body[y:]
x=body.index('\\begin{equation}',body.index('\\subsection{定位效果的综合评价与选点决策}'));y=body.index('\\end{equation}',x)+len('\\end{equation}')
body=body[:x]+r'''\begin{equation}
\begin{aligned}
 J(q)&=\mathbb E[\rho_Z(q)\mid I_1,q]\\
 &=P_{\mathrm H}(q)\rho_{\mathrm H}(q)+P_{\mathrm N}(q)\rho_{\mathrm N}(q)
 +\int_0^{2\pi}f_\Theta(\theta;q)\rho_\theta(q)\,\mathrm d\theta.
\end{aligned}
\label{eq:q2-pair-expected-objective}
\end{equation}'''+body[y:]
replace('右端第一项对应无信号的结果，第二项将各种正常示向度对应的损失按概率密度积分。强信号能够直接完成原地定位，损失为零，所以不再单列一项。','右端依次累加强信号、无信号和正常示向度对应的剩余半径，其中前两项按反馈概率加权，正常示向度按预测密度积分。')
replace('这里允许移动到剩余区域的最小包围圆圆心，与前文“在当前检测点原地完成光学定位”的条件不同。','此时移动到剩余区域的最小包围圆圆心，即可保证进入光学定位范围。')
replace('无信号虽然不能原地定位，但也可能将可行区域缩小到足以确定清除位置。','无信号也可能使剩余区域满足这一条件。')
replace('表中完成概率为100\\%而期望损失仍为正，是因为检测点未必能够原地光学定位；允许随后移动到剩余区域的圆心时，则可无需补测完成定位。上述概率均是给定先验与首次观测下的预测值。','上述结果表明，首次位置与示向度共同决定第二次检测能够达到的定位精度和完成概率。')
replace('并加入初始区域圆心或已有优选点作为参考起点','并加入初始区域圆心作为参考起点')
replace('新增两组情形的期望损失在提高精度前后变化小于','各组优选点的期望损失在提高精度前后变化小于')
replace('并用每组20000次联合先验抽样核对期望损失与完成概率。','并对8个代表选点分别进行20000次联合先验抽样，核对期望损失与完成概率。')
# Keep the computation qualification brief and affirmative.
replace('数值搜索与这些检查提供的是优选解及其计算依据，不构成连续空间中的全局最优证明。','下文报告经过上述搜索与核验得到的数值优选点。')
replace('图~\\ref{fig:q2-candidates} 将这些结果画在位置平面和指标平面上：左图显示两支镜像候选点，二者之间的位置不属于已计算的候选点；右图的曲线逐渐变平，说明继续提高完成概率需要付出更多期望损失。','图~\\ref{fig:q2-candidates} 将这些结果画在位置平面和指标平面上。左图显示权重变化对应的两支镜像候选点；右图的曲线逐渐变平，说明完成概率越接近本次搜索得到的最大值，进一步提高它所需增加的期望损失越多。')
# Replace the two complete tables from freshly verified numerical rows.
rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((ROOT/'results/typical_cases.csv').open())];origin=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((ROOT/'results/origin_weights.csv').open())]
def table(caption,label,headers,rows):
 return '\\begin{table}[htbp]\n  \\centering\n  \\caption{'+caption+'}\n  \\label{'+label+'}\n  \\small\n  \\renewcommand{\\arraystretch}{1.08}\n  \\begin{tabular}{'+('r'*len(headers))+'}\n    \\toprule\n    '+' & '.join(headers)+' \\\\\n    \\midrule\n'+''.join('    '+' & '.join(row)+' \\\\\n' for row in rows)+'    \\bottomrule\n  \\end{tabular}\n\\end{table}'
for label,new in [('tab:q2-typical-results',table('典型首次观测下的数值优选点（\\(w=0.5\\)）','tab:q2-typical-results',[r'\(a\) / 米',r'\(\beta\) / 度',r'第二检测点 \(q\) / 米',r'\(J(q)\) / 米',r'\(P_{\mathrm{finish}}(q)\) / \%'],[[f"{z['a_m']:g}",f"{z['beta_deg']:g}",f"\\(({z['x_global']:.1f},\\,{z['y_global']:.1f})\\)",f"{z['J']:.2f}",f"{min(1,z['P_finish'])*100:.2f}"] for z in rows])),('tab:q2-origin-weights',table('原点、正东算例中不同权重的选点与定位效果','tab:q2-origin-weights',[r'权重 \(w\)',r'第二检测点 \(q\) / 米',r'\(J(q)\) / 米',r'\(P_{\mathrm{finish}}(q)\) / \%'],[[f"{z['w']:g}",f"\\(({z['x_global']:.1f},\\,\\pm{abs(z['y_global']):.1f})\\)",f"{z['J']:.2f}",f"{z['P_finish']*100:.2f}"] for z in origin]))]:
 old=next(m.group(0) for m in re.finditer(r'\\begin\{table\}.*?\\end\{table\}',body,re.S) if label in m.group(0));body=body.replace(old,new)
# Check all numerical prose remains accurate at displayed precision.
r0,rm,r1=[next(z for z in origin if z['w']==w) for w in [0,.5,1]]
assert f"{rm['J']-r0['J']:.2f}"=='0.60' and f"{100*(rm['P_finish']-r0['P_finish']):.2f}"=='10.71'
body=body.replace('10.72个百分点','10.71个百分点')
# Updated computations differ just enough near a rounding boundary: 10.715 -> 10.71459.
newpath='../正式题目工作区/B题/第二问建模/论文定稿版/'+ROOT.name+'/figures/'
s=s[:a]+body+s[b:];s=re.sub(r'\\graphicspath\{[^\n]+',lambda m:'\\graphicspath{{./}{'+newpath+'}}',s)
(repo/'templates/论文模版.tex').write_text(s);(repo/'梳理/论文初稿.tex').write_text(s);(model/'第二问正文.tex').write_text(body.rstrip()+'\n')
p=model/'第二问模型.tex';v=p.read_text();v=re.sub(r'\\graphicspath\{[^\n]+',lambda m:'\\graphicspath{{./}{'+ROOT.name+'/figures/}}',v);p.write_text(v)
(ROOT/'results/问题二完整正文.tex').write_text(body.rstrip()+'\n')
print('Updated three TeX bodies, unified radius loss and strong-signal expectation term; tables and graphics use new run.')
