from pathlib import Path
import csv,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];repo=next(p for p in ROOT.parents if (p/'templates/论文模版.tex').exists());model=ROOT.parent
st=json.loads((ROOT/'inputs/manifest_start.json').read_text())
for rel in ['templates/论文模版.tex','梳理/论文初稿.tex','正式题目工作区/B题/第二问建模/论文定稿版/第二问正文.tex']:
 assert hashlib.sha256((repo/rel).read_bytes()).hexdigest()==st['pre_edit_hashes'][rel],f'Concurrent edit: {rel}'
s=(repo/'templates/论文模版.tex').read_text();a=s.index('\\subsection{由权重变化确定候选区域}');end=s.index('\\section{问题三的模型与求解}',a);old=s[a:end]
fig=re.search(r'\\begin\{figure\}.*?\\label\{fig:q2-candidates\}.*?\\end\{figure\}',old,re.S).group()
old_numeric=old[old.index('数值计算时，'):old.index('\\begin{figure}')]
replacement='实际计算时，对若干权重分别求解并汇集优选点。候选区域可能表现为曲线上的点集或若干分离部分，不一定具有非零面积；具体求解方法与结果如下。\n\n'
base=old.replace(old_numeric,replacement).replace(fig+'\n\n','').replace('\\FloatBarrier\n\n','')
algorithm=r'''\subsection{数值求解方法}

对一般的 \((a,\beta)\)，反馈区域随检测点改变，评价函数同时包含分段概率积分和最小包围圆计算，难以写成统一、简洁的显式选点公式。因此，本文采用\textbf{确定性数值积分与网格、多初值局部搜索相结合的方法}，输入首次观测及权重，输出检测点和两项评价指标。

\textbf{第一步：构造区域与搜索范围。} 由 \((a,\beta)\) 计算 \(K_1\) 和归一化系数 \(C_1\)，检查首次观测是否可行。计算时以首次点为临时原点、首次示向为横轴，便于处理狭窄角域；最终将选点坐标平移、旋转回题目的坐标系。若首次区域已满足20米包围圆条件，则直接报告无需再次测向。

\textbf{第二步：计算一个检测点的评价值。} 固定 \(q\)，分别构造强信号、无信号和各正常读数对应的区域，用边界交点与圆弧计算最小包围圆。位置积分在极坐标下进行，包含面积因子 \(r\)；在接收权重和区域约束变化处划分积分区间，再用高斯求积计算反馈概率。对正常示向度的外层积分，还要在区域形状变化及包围圆半径穿过20米的位置分段，并自适应细分，从而分别累加 \(J(q)\) 与 \(P_{\mathrm{finish}}(q)\)。这种确定性计算避免了随机抽样波动干扰相近检测点的比较。

\textbf{第三步：搜索优选位置。} 先在搜索范围的外包矩形内布置100米网格，再在可行区域附近补充较密的网格与沿示向方向的采样点。每次评价均检查 \(q\ne s_1\) 且距 \(K_1\) 不超过1500米，不合格的位置不参与比较。对固定权重，选取5个位置相互分开的较优网格点，并加入初始区域圆心或已有优选点作为参考起点，分别进行 Nelder--Mead 单纯形搜索。该方法只比较函数值，适合本模型中导数不易稳定计算的情形；随后对两个较优结果提高积分精度并再次细化。局部细化以坐标收缩至厘米量级、目标值极差不超过 \(2\times10^{-9}\) 为停止条件，最多迭代130次。同一点的两项指标可供不同权重复用。

\textbf{第四步：复算与核验。} 最终候选点采用更高阶求积和更密的阈值扫描复算，并检查0.1、1、5米邻域内是否存在更优点。新增两组情形的期望损失在提高精度前后变化小于 \(2\times10^{-6}\) 米，概率归一化残差小于 \(10^{-7}\)。另以独立射线交区间和支撑圆计算核查区域几何，并用每组20000次联合先验抽样核对期望损失与完成概率。数值搜索与这些检查提供的是优选解及其计算依据，不构成连续空间中的全局最优证明。

\subsection{求解结果与第二检测点的选择}

\subsubsection{不同首次观测下的典型结果}

为分辨首次位置与示向度的影响，表~\ref{tab:q2-typical-results} 统一取 \(w=0.5\)，比较圆心、非圆心的不同朝向及靠近边界的情形。表中均使用以目标圆心为原点的坐标，存在等效选点时列出一个代表。

'''
def table(caption,label,headers,rows):
 return '\\begin{table}[htbp]\n  \\centering\n  \\caption{'+caption+'}\n  \\label{'+label+'}\n  \\small\n  \\renewcommand{\\arraystretch}{1.08}\n  \\begin{tabular}{'+('r'*len(headers))+'}\n    \\toprule\n    '+' & '.join(headers)+' \\\\\n    \\midrule\n'+''.join('    '+' & '.join(row)+' \\\\\n' for row in rows)+'    \\bottomrule\n  \\end{tabular}\n\\end{table}\n\n'
rows=list(csv.DictReader((ROOT/'results/typical_cases.csv').open()));origin=list(csv.DictReader((ROOT/'results/origin_weights.csv').open()))
typical=table('典型首次观测下的数值优选点（\\(w=0.5\\)）','tab:q2-typical-results',[r'\(a\) / 米',r'\(\beta\) / 度',r'第二检测点 \(q\) / 米',r'\(J(q)\) / 米',r'\(P_{\mathrm{finish}}(q)\) / \%'],[[str(int(float(z['a_m']))),str(int(float(z['beta_deg']))),f"\\(({float(z['q_x_m']):.1f},\\,{float(z['q_y_m']):.1f})\\)",f"{float(z['J_m']):.2f}",f"{min(1,float(z['P_finish']))*100:.2f}"] for z in rows])
explain=r'''表~\ref{tab:q2-typical-results} 说明，首次点到圆心的距离相同，并不必然对应相近的定位效果。例如，\(a=1200\) 米时，\(30^\circ\) 方向的初始区域受圆域边界截断较多，第二次检测的完成概率可达100\%；\(90^\circ\) 方向保留范围更长，完成概率约为40.38\%。\(150^\circ\) 方向的首次角域在接收范围内完整落入圆域，其定位几何与圆心算例等价，因此平移、旋转选点后得到相同的两项指标。靠近边界的 \(a=1700\)、\(\beta=0\) 情形则具有更小的剩余不确定性。

表中完成概率为100\%而期望损失仍为正，是因为检测点未必能够原地光学定位；允许随后移动到剩余区域的圆心时，则可无需补测完成定位。上述概率均是给定先验与首次观测下的预测值。

\subsubsection{首次位于原点、示向正东时的权重比较}

当 \(a=0,\beta=0\) 时，关于横轴对称的两个检测点具有相同评价。表~\ref{tab:q2-origin-weights} 列出11个权重对应的数值优选点，以 \(\pm\) 同时表示两支对称候选位置。

'''
weights=table('原点、正东算例中不同权重的选点与定位效果','tab:q2-origin-weights',[r'权重 \(w\)',r'第二检测点 \(q\) / 米',r'\(J(q)\) / 米',r'\(P_{\mathrm{finish}}(q)\) / \%'],[[f"{float(z['w']):g}",f"\\(({float(z['q_x_m']):.1f},\\,\\pm{float(z['q_abs_y_m']):.1f})\\)",f"{float(z['J_m']):.2f}",f"{float(z['P_finish'])*100:.2f}"] for z in origin])
finish=r'''由表~\ref{tab:q2-origin-weights}，只考虑期望损失时，优选点约为 \((906.6,\pm572.8)\) 米。两项归一化指标等权时，选取 \(w=0.5\)，得到 \(q\approx(813.8,\pm521.0)\) 米；相较 \(w=0\)，期望损失增加约0.60米，完成概率提高约10.72个百分点。若只追求完成概率，则取 \(w=1\)，优选点约为 \((705.5,\pm470.7)\) 米，完成概率约为40.57\%，相应期望损失增至28.02米。

图~\ref{fig:q2-candidates} 将这些结果画在位置平面和指标平面上：左图显示两支镜像候选点，二者之间的位置不属于已计算的候选点；右图的曲线逐渐变平，说明继续提高完成概率需要付出更多期望损失。由此，本问的输出是随权重变化的一组候选位置；确定定位偏好后，采用对应权重的选点。对于表外的首次观测，按前述数值流程重新求解即可。

'''
section=base+algorithm+typical+explain+weights+finish+fig+'\n\n\\FloatBarrier\n\n'
s=s[:a]+section+s[end:]
(repo/'templates/论文模版.tex').write_text(s);(repo/'梳理/论文初稿.tex').write_text(s)
a=s.index('\\section{问题二的模型与求解}');b=s.index('\\section{问题三的模型与求解}',a);(model/'第二问正文.tex').write_text(s[a:b].rstrip()+'\n')
(ROOT/'results/新增求解与结果正文.tex').write_text(algorithm+typical+explain+weights+finish)
print('Added solver workflow, 5-case table, 11-weight table; moved candidate figure alongside results.')
