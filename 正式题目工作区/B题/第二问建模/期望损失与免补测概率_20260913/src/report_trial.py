"""Readable report and scientific plots from saved outputs; does not optimize."""
from pathlib import Path
import csv,datetime,hashlib,json,os,platform,sys
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/q2-weight-mpl-cache')
# Optional pre-existing plotting wheels; ordinary installations work without this fallback.
try:import matplotlib
except ImportError:
 if Path('/private/tmp/bq2-plot-deps').exists():sys.path.insert(0,'/private/tmp/bq2-plot-deps')
 import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

def main():
 cases=[json.loads(f.read_text()) for f in sorted((ROOT/'results').glob('*/summary.json'))]
 origin=next(c for c in cases if c['a']==0);rows=origin['candidates'];v=json.loads((ROOT/'verification/summary.json').read_text());audit=json.loads((ROOT/'verification/shifted_grid_audit.json').read_text())
 font=Path('/Applications/Microsoft Word.app/Contents/Resources/DFonts/SimHei.ttf')
 if font.exists():font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
 plt.rcParams.update({'font.size':11,'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'path'})
 fig=plt.figure(figsize=(12.8,5.3));grid=fig.add_gridspec(1,3,width_ratios=[1.1,1,.035],wspace=.3);ax=fig.add_subplot(grid[0]);bx=fig.add_subplot(grid[1]);cx=fig.add_subplot(grid[2]);cmap=plt.get_cmap('viridis');norm=plt.Normalize(0,1)
 weights=np.array([r['w'] for r in rows]);x=np.array([r['x_global'] for r in rows]);y=np.array([r['y_global'] for r in rows]);loss=np.array([r['J'] for r in rows]);prob=np.array([r['P_finish']*100 for r in rows])
 angles=np.linspace(-np.pi/180,np.pi/180,120);px=np.r_[5*np.cos(angles[0]),1500*np.cos(angles),5*np.cos(angles[::-1])];py=np.r_[5*np.sin(angles[0]),1500*np.sin(angles),5*np.sin(angles[::-1])]
 ax.fill(px,py,color='#d4dee2',label='首次源位置可行区域')
 for sign in [1,-1]:
  ax.plot(x,sign*y,color='#9199a0',lw=1.2,zorder=2);ax.scatter(x,sign*y,c=weights,cmap=cmap,norm=norm,s=35,zorder=3,edgecolors='white',linewidths=.5)
 ax.scatter([0],[0],marker='*',s=120,c='#222222',zorder=4,label='首次检测点')
 for w,offset in [(0,(10,13)),(.5,(10,15)),(1,(-12,-25))]:
  i=list(weights).index(w);ax.annotate(f'w={w:g}',(x[i],y[i]),xytext=offset,textcoords='offset points',fontsize=10)
 ax.text(900,70,'首次可行区域',ha='center',color='#53616b',fontsize=10)
 ax.set(xlim=(-100,1590),ylim=(-690,690),xlabel='横坐标 / 米',ylabel='纵坐标 / 米',title='(a) 不同权重下的候选点')
 ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.15);ax.text(.03,.035,'上下两支由场景对称性得到\n连线仅表示权重变化顺序',transform=ax.transAxes,fontsize=9,color='#53616b')
 bx.plot(loss,prob,color='#9199a0',lw=1.3);scatter=bx.scatter(loss,prob,c=weights,cmap=cmap,norm=norm,s=48,edgecolors='white',linewidths=.6,zorder=3)
 for w,offset in [(0,(12,-1)),(.2,(13,-4)),(.5,(10,-16)),(.8,(-20,12)),(1,(-32,13))]:
  i=list(weights).index(w);bx.annotate(f'w={w:g}',(loss[i],prob[i]),xytext=offset,textcoords='offset points',fontsize=10)
 bx.set(xlabel='原模型期望定位损失 J / 米',ylabel='第二次检测后无需补测的概率 / %',title='(b) 定位损失与完成概率的取舍',xlim=(24.9,28.3),ylim=(24.8,43));bx.grid(alpha=.2)
 fig.colorbar(scatter,cax=cx,label='完成概率权重 w')
 fig.suptitle('首次在原点、示向正东：增加完成概率权重后的选点结果',fontsize=14,y=.98)
 fig.subplots_adjust(top=.86,bottom=.14,left=.06,right=.93)
 fig.savefig(ROOT/'figures/权重扫描与候选点.png',dpi=200)
 fig.savefig(ROOT/'figures/权重扫描与候选点.svg')
 plt.close(fig)
 allrows=[]
 for case in cases:
  for r in case['candidates']:
   for sign in ([1,-1] if case['mirror_equivalence'] and abs(r['y_global'])>1e-7 else [1]):
    allrows.append(dict(case=case['case'],a=case['a'],beta_deg=case['beta_deg'],w=r['w'],x=r['x_global'],y=sign*r['y_global'],J=r['J'],P_finish=min(1,max(0,r['P_finish'])),P_onsite=min(1,max(0,r['P_onsite'])),representative_only=True))
 with (ROOT/'results/全部权重候选点.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(allrows[0]));writer.writeheader();writer.writerows(allrows)
 table='\n'.join(f"| {r['w']:g} | ({r['x_global']:.2f}, ±{r['y_global']:.2f}) | {r['J']:.4f} | {100*r['P_finish']:.2f}% |" for r in rows)
 casetable='\n'.join(f"| {c['a']:g} | {c['beta_deg']:g}° | ({c['candidates'][0]['x_global']:.2f}, {c['candidates'][0]['y_global']:.2f}) | {c['candidates'][0]['J']:.4f} | {min(100,c['candidates'][0]['P_finish']*100):.2f}% |" for c in cases if c['a']!=0)
 total=sum(c['elapsed_seconds'] for c in cases);n=sum(c['evaluation_count'] for c in cases)
 report=f'''# 期望损失与免补测概率加权实验结果

日期：2026-09-13。模型 Q2-expected-finish-M01-v01，算法 A01，运行 R001。状态：完成探索性数值求解与分项核查，尚未被采用到论文；没有修改论文、原模型、旧代码或旧结果。

## 评价指标与权重

原模型 J(q) 完整保留，只有可以在当前检测点原地完成光学定位的反馈才计零损失，其余反馈取剩余区域的最小包围圆半径。新增 P_finish(q)=Pr(rho(K_Z(q))<=20 | I1,q)，衡量第二次检测后是否已经无需继续无线电测向；允许再移动到包围圆圆心，随后完成光学定位。强信号、无信号及正常读数均纳入该事件。

最小化 F_w(q)=(1-w)J(q)/20+w[1-P_finish(q)]。w是完成概率的权重，0为原模型，1为只最大化完成概率。20米取自任务的光学定位尺度，用于消除量纲；这是一种评价约定，不是由题面推出的唯一归一化。改变尺度会改变权重的解释，不应将w=0.5描述为客观最优的偏好。

在w=1处，数值相同的完成概率优先取J较小的代表点。程序仅为数值平局加10^-10 J/20；在本轮报告精度上不改变概率最优值，不把单个代表点称为全部概率最优点。

## 原点、正东基准情景

目标圆心为原点，首次检测点为(0,0)，第一次示向度为0°。下表单位为米；正负纵坐标分别表示由对称性得到的两支。坐标显示精度不是连续最优坐标的误差保证。

| 完成概率权重 w | 第二检测点 | 期望定位损失 J | 无需补测概率 |
|---:|---|---:|---:|
{table}

![权重扫描](figures/权重扫描与候选点.png)

这组11个权重给出北侧11个代表候选点及其南侧镜像，共22个点。权重增加时，候选点在本次搜索中逐步向首次检测点一侧移动，完成概率提高，期望半径损失也增加。这里只得到离散权重对应的点集；连线用于呈现变化顺序，不表示已证明连线上每个位置都最优，也不把两支之间填充为候选区域。

与w=0相比，w=0.2仅将J提高约0.1213米，完成概率增加约6.22个百分点；w=0.5将J提高约0.5989米，完成概率增加约10.72个百分点。w=1的完成概率最高候选值约40.57%，但J增至28.0245米。后段概率收益逐渐减小。w=0.2至0.5值得作为较温和的折中进行比较，尚不存在唯一正确的权重。

所有这些原点候选的原地光学定位概率均为0。表中的完成概率表示反馈之后，剩余区域能被某个20米圆覆盖，机器狗仍可能需要移动；它不是在第二检测点原地找到源的概率，也不是源以该概率落入随意选定的20米圆。

## 边界情景检查

| 首次点横坐标 a | 示向度 beta | 各权重共同采用的代表点 | J | 无需补测概率 |
|---:|---:|---|---:|---:|
{casetable}

在a=1700的两个情景中，原期望损失的最好候选已经达到约100%的完成概率，新增指标没有形成有意义的折中，按J择优仍选择同一点。在w=1时可能有许多同为100%的位置，这里按J给出一个代表。对a=1780、beta=0°，首次区域本身已有半径小于20米的包围圆，推荐圆心同时取得J=0与P_finish=1，故所有权重均达到理论全局下界0。这些只是四个代表情景，不代表整个连续参数域。

## 算法、预算与实际运行

采用原模型的圆弧几何与分段Gauss积分。新增完成事件的半径20米交点搜索，将正常反馈角度在这些位置分段后再积分；搜索用较低精度，最后采用高精度复算。阈值根搜索属于数值扫描与二分，不声称穷尽所有可能的连续几何事件。

外层采用100米覆盖网格、源区域附近细网格、约5个分散初值加原模型基线初值、Nelder-Mead局部细化，以及两处不同低值区域的高精度再搜索。对称情景在上半平面搜索，最终独立复算镜像；一般情景保留两侧。每个试探点检查q不同于首次点、到K1的距离不超过1500米。局部搜索最多150次迭代，高精度再搜索最多130次，达到上限会保留诊断。J与P的共同优势用于边界情景的权重复用，不用重复求相同问题。

四情景主搜索共评价{n:,}个位置与精度组合，分情景实测耗时合计{total:.2f}秒；部分情景并行执行，该合计不是实际墙钟时间，也不包含独立核查和绘图。初次加载、机器负载与积分难度会影响耗时。原点另使用50米、偏移25米的覆盖网格补查，评价{audit['evaluations']:,}次，未找到优于所报加权候选的网格节点。最终还在0.1、1、5米尺度上作邻域复核，未发现更好点。

## 数值核查

- 对8个代表点进行积分精度和阈值扫描加密；最高两档J差最大{v['max_J_convergence_difference']:.3g}米，完成概率差最大{v['max_P_convergence_difference']:.3g}。这些是固定点的数值一致性，不是全局搜索误差界。
- 新实现对原J的复算，与冻结原实现的最大差为{v['max_J_regression_difference']:.3g}米；核查新增概率未误改原目标。
- 概率归一化残差最大{v['max_probability_residual']:.3g}；检查了P_finish不小于原地定位概率及强信号概率，镜像核查通过。
- 独立射线交区与有限支撑圆枚举完成{v['independent_geometry_checks']}组检查，包含20米阈值两侧。独立点集半径下界与主算法连续区域上界最大差约{v['max_independent_radius_gap']:.6f}米，抽查中没有无法判定阈值侧别的情况；它不构成全域几何误差证明。
- 对6个代表点各模拟60,000个相容场景，共{v['simulation_samples']:,}个有效场景。J的最大标准化偏差为{v['max_simulation_J_zscore']:.3f}个标准误，完成概率为{v['max_simulation_P_zscore']:.3f}个标准误，未发现明显冲突。模拟共享几何内核，只用于独立核对概率更新与期望积分；几何由另一条射线途径检查。每个场景始终共享固定的接收半径，新地点误差在该场景内取固定值，没有同地点重复测量平均。

专门检查了一个无信号也足以完成测向的算例：首次点(1700,0)、示向正东，第二点取(770,0)。无信号概率约1.6241%，该分支剩余区域的包围圆半径约15.0754米，而当前点到区域最远距离约1030米。因此该分支计入免补测概率，但不计入原地光学定位概率。它是分支核查点，不是优选点。

## 结论与限制

新增指标在原点基准中提供了实际区分能力，可以用较小的平均定位损失增量换取更高的免补测概率；它不是所有情景下都能改变决策。当前证据支持进一步讨论采用方式，不足以宣布连续全局最优，也不能直接把点集当成有面积的候选区域。期望损失与完成概率均依赖原模型的均匀先验及独立性假设，本次没有进行先验敏感性研究。

原论文及基础研究文件未修改、未提交、未推送。完整候选点见[CSV](results/全部权重候选点.csv)，分项验证见 `verification/`，模型与输入快照见 `inputs/`。重新计算应运行 `src/reproduce.py`，该入口会创建独立的复现目录，保留本次结果。
'''
 (ROOT/'结果汇报.md').write_text(report)
 (ROOT/'README.md').write_text('# 期望损失与免补测概率加权实验\n\n状态：探索性求解与分项验证完成，尚未采用到论文。\n\n请先阅读[结果汇报](结果汇报.md)。原点情景下11个权重得到22个含镜像的代表候选点；三组边界情景用于检查指标退化。原点基准存在有意义的折中，边界情景未必改变选点。\n\n- [全部候选点](results/全部权重候选点.csv)\n- [候选点与指标图](figures/权重扫描与候选点.png)\n- [矢量图](figures/权重扫描与候选点.svg)\n- [验证汇总](verification/summary.json)\n- [初始模型与来源清单](inputs/manifest_start.json)\n\n权重模型为 (1-w)J/20+w(1-P_finish)，w是免补测概率的权重。J沿用当前论文，P_finish采用区域包围圆半径不超过20米的条件，允许检测后移至圆心；不等同于原地光学定位。\n\n运行 `python src/reproduce.py` 创建独立复现目录。需要Python、NumPy、C++17编译器；绘图另需Matplotlib和中文字体。复现不会覆盖本目录现有结果。\n')
 manifest={'finished_at':datetime.datetime.now().isoformat(),'platform':platform.platform(),'python':sys.version,'plot_numpy':np.__version__,'matplotlib':matplotlib.__version__,'source_core_note':'The numeric evaluator was unchanged after the main run; baseline/cuts diagnostics and reproduction/report scripts were added for verification.','files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest_final.json' and '__pycache__' not in p.parts},'paper_adopted':False,'nonzero_global_optimality_certified':False}
 (ROOT/'manifest_final.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print('Report and plots saved; total search evaluations',n,'sum seconds',total)

if __name__=='__main__':main()
