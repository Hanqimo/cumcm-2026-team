"""Insert only figure material into the live authoritative paper; guard concurrent edits."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];state=json.loads(Path('/private/tmp/q2_three_figures_state.json').read_text());repo=Path(state['root'])
main=repo/'templates/论文模版.tex';mirror=repo/'梳理/论文初稿.tex';body=ROOT.parent/'第二问正文.tex';wrapper=ROOT.parent/'第二问模型.tex'
for p in [main,mirror,body,wrapper]:
 assert hashlib.sha256(p.read_bytes()).hexdigest()==state['pre_edit_hashes'][str(p.relative_to(repo))],f'Concurrent edit: {p}'
s=main.read_text();assert 'fig:q2-posterior' not in s
fig1=r'''\begin{figure}[htbp]
  \centering
  \includegraphics[width=160mm]{q2_posterior.pdf}
  \caption{首次正常示向度观测前后的位置信息（\(a=0,\beta=0\)）。右图按源距和相对示向角展开狭窄角域，颜色仍表示单位面积上的位置概率密度。}
  \label{fig:q2-posterior}
\end{figure}'''
fig2=r'''\begin{figure}[htbp]
  \centering
  \includegraphics[width=160mm]{q2_feedback.pdf}
  \caption{第二次反馈的预测分布与剩余区域（\(a=0,\beta=0,w=0.5\)，\(q=(813.82,521.02)\) 米）。本例强信号与无信号概率均为0，阴影面积即完成概率；两个下图采用相同长度尺度，对比剩余区域能否被20米圆覆盖。}
  \label{fig:q2-feedback}
\end{figure}'''
fig3=r'''\begin{figure}[htbp]
  \centering
  \includegraphics[width=160mm]{q2_candidates.pdf}
  \caption{11个权重下的候选检测点及评价指标（\(a=0,\beta=0\)）。颜色表示完成概率权重，虚线仅连接相邻权重的数值结果，不表示点间所有位置都已入选。}
  \label{fig:q2-candidates}
\end{figure}'''
old='其中 \\(C_1\\) 是归一化系数。该结果说明，距离超过1000米后，越远的位置得到的权重越低，因为能解释首次接收的半径取值越来越少。'
assert s.count(old)==1;s=s.replace(old,old+'图~\\ref{fig:q2-posterior} 展示了首次观测带来的区域筛选与位置权重变化。')
anchor='\\subsubsection{第二次反馈的概率预测}';assert s.count(anchor)==1;s=s.replace(anchor,fig1+'\n\n'+anchor)
anchor='\\subsection{由权重变化确定候选区域}';assert s.count(anchor)==1
s=s.replace(anchor,'图~\\ref{fig:q2-feedback} 给出了 \\(w=0.5\\) 时的具体例子。不同示向度留下的区域大小不同，将满足20米包围圆条件的反馈所占概率相加，就得到该点的完成概率。\n\n'+fig2+'\n\n'+anchor)
old='在原点、正东的算例中，已计算的11个权重得到两支互为镜像的候选点序列；绘图应保留这两支，不把中间未入选的位置填成候选区域。'
new='在原点、正东的算例中，已计算的11个权重得到两支互为镜像的候选点序列，如图~\\ref{fig:q2-candidates} 所示；两支之间的位置不属于已计算的候选点。'
assert old in s;s=s.replace(old,new)
anchor='\\section{问题三的模型与求解}';assert s.count(anchor)==1;s=s.replace(anchor,fig3+'\n\n\\FloatBarrier\n\n'+anchor)
path='../正式题目工作区/B题/第二问建模/论文定稿版/论文插图_20260913/figures/'
assert '\\graphicspath{{./}}' in s;s=s.replace('\\graphicspath{{./}}','\\graphicspath{{./}{'+path+'}}')
s=s.replace('\\usepackage{float}','\\usepackage{float}\n\\usepackage{placeins}')
start=s.index('\\section{问题二的模型与求解}');end=s.index('\\section{问题三的模型与求解}',start)
newbody=s[start:end].rstrip()+'\n'
w=wrapper.read_text().replace('\\graphicspath{{./}}','\\graphicspath{{./}{论文插图_20260913/figures/}}').replace('\\usepackage{float}','\\usepackage{float}\n\\usepackage{placeins}')
main.write_text(s);mirror.write_text(s);body.write_text(newbody);wrapper.write_text(w)
(ROOT/'data/figure_captions.tex').write_text('\n\n'.join([fig1,fig2,fig3])+'\n')
(ROOT/'verification/inserted_files.json').write_text(json.dumps({str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [main,mirror,body,wrapper]},ensure_ascii=False,indent=2))
print('Inserted 3 figures. Main and mirror identical; standalone body synchronized.')
