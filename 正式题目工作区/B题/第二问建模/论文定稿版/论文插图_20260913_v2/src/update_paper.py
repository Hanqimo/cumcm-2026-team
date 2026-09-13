from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parents[1];st=json.loads((ROOT/'inputs/revision.json').read_text());repo=Path(st['root']);model=ROOT.parent
main=repo/'templates/论文模版.tex';mirror=repo/'梳理/论文初稿.tex';body=model/'第二问正文.tex';wrapper=model/'第二问模型.tex'
for p in [main,mirror,body,wrapper]:assert hashlib.sha256(p.read_bytes()).hexdigest()==st['pre_edit_hashes'][str(p.relative_to(repo))],f'concurrent edit: {p}'
s=main.read_text()
s=s.replace('图~\\ref{fig:q2-posterior} 展示了首次观测带来的区域筛选与位置权重变化。','')
anchor='接收半径本身也需要更新。'
explain=r'''图~\ref{fig:q2-posterior} 固定首次检测点为 \(s_1=(1200,0)\) 米，比较 \(\beta=30^\circ\) 与 \(90^\circ\) 时的后验分布。示向度决定保留哪个角域，而圆域边界进一步限制源的位置：\(30^\circ\) 方向的角域较早遇到边界，后验集中在较小的区域；\(90^\circ\) 方向保留的距离范围更长，其中超过1000米的部分还因接收概率下降而降低权重。这说明，当圆域边界参与截断时，示向度会改变后验分布的形状与密度大小。两幅热力图采用同一色标，并按源距与相对示向角展开显示；颜色仍表示单位面积上的位置概率密度。

'''
assert s.count(anchor)==1;s=s.replace(anchor,explain+anchor)
pat=r'\\begin\{figure\}\[htbp\].*?\\end\{figure\}'
blocks=re.findall(pat,s,re.S)
old=next(b for b in blocks if '\\label{fig:q2-posterior}' in b)
new=r'''\begin{figure}[htbp]
  \centering
  \includegraphics[width=160mm]{q2_posterior_general.pdf}
  \caption{非圆心检测点处，不同首次示向度对应的后验位置密度}
  \label{fig:q2-posterior}
\end{figure}''';s=s.replace(old,new)
# Region example follows the completion definition; no weight is used before its definition.
anchor='上述两个指标分别反映平均剩余不确定性和本次检测后结束测向的可能性。'
region=r'''图~\ref{fig:q2-feedback-regions} 具体说明了20米包围圆条件。这里取首次点为原点、首次示向正东，第二检测点为 \(q=(813.82,521.02)\) 米。若新读数为 \(270^\circ\)，剩余区域的包围圆半径约为16.87米，移动到其圆心即可保证清除，无需补测；若读数为 \(300^\circ\)，半径约为30.43米，任何20米圆都无法覆盖整个区域，因而仍需补测。两幅局部图使用相同的长度尺度，虚线圆的半径均为20米。

\begin{figure}[htbp]
  \centering
  \includegraphics[width=130mm]{q2_feedback_regions.pdf}
  \caption{两种示向度反馈下的剩余区域与完成条件}
  \label{fig:q2-feedback-regions}
\end{figure}

'''
assert s.count(anchor)==1;s=s.replace(anchor,region+anchor)
oldpara='图~\\ref{fig:q2-feedback} 给出了 \\(w=0.5\\) 时的具体例子。不同示向度留下的区域大小不同，将满足20米包围圆条件的反馈所占概率相加，就得到该点的完成概率。'
newpara=r'''沿用图~\ref{fig:q2-feedback-regions} 的原点算例，该检测点是 \(w=0.5\) 时得到的数值优选点。图~\ref{fig:q2-feedback} 给出其第二次示向度的预测密度，并用阴影标出满足完成条件的反馈。本例强信号与无信号的概率均为0，因此阴影面积就是完成概率，约为37.34\%。密度较高的读数未必能使区域缩小到20米圆内，这说明选点时需要同时考虑反馈出现的可能性及其留下的区域大小。'''
assert oldpara in s;s=s.replace(oldpara,newpara)
old=next(b for b in blocks if '\\label{fig:q2-feedback}' in b)
new=r'''\begin{figure}[htbp]
  \centering
  \includegraphics[width=150mm]{q2_feedback_distribution.pdf}
  \caption{第二次示向度的预测密度及满足完成条件的反馈}
  \label{fig:q2-feedback}
\end{figure}''';s=s.replace(old,new)
anchor='两支之间的位置不属于已计算的候选点。对于其他首次位置和示向度，需要重新计算相应的候选位置。'
replacement='两支之间的位置不属于已计算的候选点。右图说明，随着完成概率权重提高，优选点的期望损失和完成概率同时上升；曲线随后逐渐变平，表示继续提高完成概率需要付出更多的期望损失。对于其他首次位置和示向度，需要重新计算相应的候选位置。'
assert anchor in s;s=s.replace(anchor,replacement)
path='../正式题目工作区/B题/第二问建模/论文定稿版/论文插图_20260913_v2/figures/'
s=s.replace('\\graphicspath{{./}', '\\graphicspath{{./}{'+path+'}')
start=s.index('\\section{问题二的模型与求解}');end=s.index('\\section{问题三的模型与求解}',start)
w=wrapper.read_text().replace('\\graphicspath{{./}', '\\graphicspath{{./}{论文插图_20260913_v2/figures/}')
main.write_text(s);mirror.write_text(s);body.write_text(s[start:end].rstrip()+'\n');wrapper.write_text(w)
(ROOT/'data/figure_captions.tex').write_text('\n\n'.join(b for b in re.findall(pat,s,re.S) if 'fig:q2-' in b))
(ROOT/'verification/updated_sources.json').write_text(json.dumps({str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [main,mirror,body,wrapper]},ensure_ascii=False,indent=2))
print('Updated body explanations and split figures; model equations unchanged.')
