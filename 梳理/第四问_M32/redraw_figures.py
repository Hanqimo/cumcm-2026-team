"""Compare frozen literature CG, archived M07 and M32; no simulation here."""
from pathlib import Path
import json,csv,shutil,hashlib,sys
import numpy as np
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence';FIG=HERE/'figures'
DATA.mkdir(exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,o):(DATA/f'{n}.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
BLUE,TEAL,ORANGE,GRAY,RED='#245B83','#26756B','#B46A24','#64717C','#A54246'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['SimSun','DejaVu Sans'],'mathtext.fontset':'stix',
 'font.size':9,'axes.labelsize':9,'axes.titlesize':9.5,'xtick.labelsize':8,'ytick.labelsize':8,
 'legend.fontsize':8,'axes.linewidth':.65,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False})
def save(f,n):
 for ext in ['pdf','svg','png']:f.savefig(FIG/f'{n}.{ext}',dpi=400)
 plt.close(f)
def clean(ax):ax.spines[['top','right']].set_visible(False)
def summary(vals):
 a=np.array(vals);mean=float(a.mean());sd=float(a.std(ddof=1));se=sd/np.sqrt(len(a))
 return dict(n=len(a),mean=mean,sd=sd,ci95=[float(x) for x in t.interval(.95,len(a)-1,loc=mean,scale=se)],
             median=float(np.median(a)),p90=float(np.quantile(a,.9)))
def independent_difference(a,b):
 a=np.asarray(a);b=np.asarray(b);u=a.var(ddof=1)/len(a);v=b.var(ddof=1)/len(b)
 df=(u+v)**2/(u*u/(len(a)-1)+v*v/(len(b)-1));d=a.mean()-b.mean()
 return dict(mean=float(d),ci95=[float(x) for x in t.interval(.95,df,loc=d,scale=np.sqrt(u+v))])


keys=['cautious','m07','m32'];names=['文献适配 CG','旧版 M07','本文 M32'];colors=[ORANGE,GRAY,BLUE]
local=read(DATA/'paired_rows.json');pair=read(DATA/'paired_analysis.json')
i=next(i for i,r in enumerate(local['m32']) if r['seed']==pair['seed'])
acts=read(DATA/'paired_actions.json')
stats=read(DATA/'official_statistics.json');raw=read(DATA/'official_rows.json')
official={k:[r for r in raw if r['strategy']==k] for k in keys}
fig,axs=plt.subplots(2,2,figsize=(6.3,4.65));fig.subplots_adjust(left=.09,right=.98,bottom=.105,top=.93,hspace=.40,wspace=.28)
for ax,k,name,color,letter in zip(axs.ravel()[:3],keys,names,colors,['a','b','c']):
 xy=np.array([[0,0]]+[a['point'] for a in acts[k]])/1000
 ax.add_patch(Circle((0,0),1.8,fill=False,ls='--',lw=.7,color=GRAY));ax.plot(*xy.T,color=color,lw=.8)
 stops=np.array([a['point'] for a in acts[k] if a['kind']=='clear' and a['success']])/1000
 ax.scatter(*stops.T,marker='x',s=15,color=color,zorder=4);ax.scatter([0],[0],s=14,facecolors='white',edgecolors=color,zorder=5)
 r=local[k][i];ax.set_title(f'({letter}) {name}：{r["time_s"]:.1f} s',fontsize=9)
 ax.set(xlim=(-2.1,2.1),ylim=(-2.1,2.1),xticks=[-1.8,0,1.8],yticks=[-1.8,0,1.8],xlabel='$x$ / km',ylabel='$y$ / km');ax.set_aspect('equal');clean(ax)
ax=axs[1,1]
for k,name,color,ls in zip(keys,names,colors,[':','--','-']):
 times=[0]+[a['time_s']/60 for a in acts[k] if a['kind']=='clear' and a['success']]
 values=list(range(len(times)));times.append(local[k][i]['time_s']/60);values.append(values[-1])
 ax.step(times,values,where='post',color=color,ls=ls,label=name,lw=1.3)
 ax.scatter(times[-1],values[-1],marker='s',s=13,color=color,zorder=4)
ax.set(xlabel='累计虚拟时间 / min',ylabel='累计成功清除数',title='(d) 相同场景的清除进度',ylim=(0,10.6));ax.legend(loc='upper left',fontsize=7.5,frameon=False);clean(ax)
save(fig,'fig04-paired-paths')
fig,axs=plt.subplots(1,2,figsize=(6.3,3.1),gridspec_kw={'width_ratios':[1.05,1]});fig.subplots_adjust(left=.11,right=.98,bottom=.23,top=.87,wspace=.35)
ax=axs[0]
for j,k in enumerate(keys):
 vals=[r['time_per_actual_target_s'] for r in official[k]];s=stats[k];lo,hi=s['ci95']
 ax.scatter(j+.2*np.sin(np.arange(30)*2.399963),vals,s=12,c=colors[j],alpha=.65)
 ax.errorbar(j,s['mean'],yerr=[[s['mean']-lo],[hi-s['mean']]],fmt='D',color='black',capsize=3,ms=4,zorder=5)
ax.set(xticks=range(3),xticklabels=['CG','M07','M32'],ylabel='单场平均时间 / (s·源$^{-1}$)',title='(a) 各 30 场独立官方演练');ax.grid(axis='y',alpha=.15);clean(ax)
ax.text(.5,-.25,'散点：单场；菱形：均值及 95% t 区间',ha='center',transform=ax.transAxes,fontsize=7.5)
ax=axs[1];left=np.zeros(3)
for i,(label,col,hatch) in enumerate(zip(['移动','测量','换频','光学'],[BLUE,TEAL,ORANGE,GRAY],['','//','xx','..'])):
 vals=np.array([stats[k]['costs'][i] for k in keys]);ax.barh(range(3),vals,left=left,height=.55,label=label,color=col,hatch=hatch,edgecolor='white',lw=.5);left+=vals
ax.set(yticks=range(3),yticklabels=['CG','M07','M32'],xlabel='场均分项时间 / (s·源$^{-1}$)',title='(b) 时间差来自哪些费用');ax.invert_yaxis();clean(ax)
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.24),ncol=4,frameon=False,fontsize=7,columnspacing=.5,handlelength=1)
save(fig,'fig03-official-comparison')
"""Rebuild Q4 figures from frozen official logs. No simulator is imported or run."""
from pathlib import Path
import json, hashlib, csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as PatchPolygon, Wedge
from shapely import wkt
from shapely.geometry import box, Point, MultiPoint
from shapely.ops import unary_union

BASE=Path(__file__).resolve().parent
OUT=BASE/'figures'
DATA=BASE/'evidence'
OUT.mkdir(parents=True,exist_ok=True); DATA.mkdir(exist_ok=True)
BLUE,TEAL,ORANGE,GRAY,RED='#245B83','#26756B','#B46A24','#64717C','#A54246'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['SimSun','DejaVu Sans'],
 'mathtext.fontset':'stix','font.size':9,'axes.labelsize':9,'axes.titlesize':9.5,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.65,
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,
 'figure.facecolor':'white','lines.linewidth':1.1})
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(fig,name):
 for ext in ('pdf','svg','png'):fig.savefig(OUT/f'{name}.{ext}',dpi=400)
 plt.close(fig)
def style(ax,equal=False):
 ax.spines[['top','right']].set_visible(False)
 if equal:ax.set_aspect('equal',adjustable='box')
def poly(ax,g,**kw):
 if g.geom_type=='Polygon':ax.add_patch(PatchPolygon(np.asarray(g.exterior.coords),**kw))
 elif hasattr(g,'geoms'):
  for sub in g.geoms:poly(ax,sub,**kw)



example=read(DATA/'joint_example.json');events=read(DATA/'joint_event_metrics.json')
reductions=[e for e in events if e['new_radius']<e['old_radius']-1e-6]
# Figure 1: schematic, no hidden official coordinates.
fig,axs=plt.subplots(1,2,figsize=(6.3,2.8));fig.subplots_adjust(left=.06,right=.98,bottom=.12,top=.85,wspace=.32)
ax=axs[0];ax.add_patch(Wedge((0,0),1.1,-90,90,facecolor=BLUE,alpha=.12));ax.add_patch(Circle((0,0),1.1,fill=False,color=GRAY,ls='--'))
ax.scatter([0],[0],marker='*',s=85,c=BLUE,zorder=3);ax.annotate('$x$',(0,0),xytext=(5,-17),textcoords='offset points')
ax.arrow(0,0,.6,0,width=.012,head_width=.06,color=BLUE);ax.text(.35,.12,'$n$')
for q,label,color,marker in [((.58,.46),'收到信号',TEAL,'o'),((-.65,.25),'背向：无信号',RED,'x'),((1.25,-.35),'超距：无信号',ORANGE,'x')]:
 ax.scatter(*q,color=color,marker=marker,s=32);ax.annotate(label,q,xytext=(0,10),textcoords='offset points',ha='center',fontsize=8)
ax.set(xlim=(-1.35,1.65),ylim=(-1.25,1.25),title='(a) 无信号对应两种原因');ax.axis('off');ax.set_aspect('equal')
ax=axs[1];ss=np.array([[-.9,-.55],[.9,-.5],[.15,.9]]);ax.add_patch(PatchPolygon(ss,facecolor=TEAL,alpha=.1,edgecolor=TEAL))
ax.scatter(*ss.T,c=TEAL,marker='s',s=35);ax.scatter(0,0,c=BLUE,marker='*',s=85)
for i,s in enumerate(ss):ax.text(*(s+np.array([.02,.08])),f'$s_{i+1}$')
ax.plot([-1.1,1.1],[0,0],ls='--',c=GRAY);ax.arrow(0,0,0,.55,width=.01,head_width=.055,color=BLUE)
ax.text(.08,.32,'$n$');ax.text(-.13,-.17,'$x$');ax.text(0,-.9,'凸组合的有向投影之和为零',ha='center',fontsize=8)
ax.set(xlim=(-1.3,1.3),ylim=(-1.1,1.15),title='(b) 凸包覆盖保证至少一站位于前向');ax.axis('off');ax.set_aspect('equal')
save(fig,'fig01-direction-coverage')

# Figure 3: actual posterior domain, selected without maximising improvement.
old=wkt.loads(example['old_region']);new=wkt.loads(example['new_region']);removed=old.difference(new)
fig,axs=plt.subplots(1,2,figsize=(6.3,3.3));fig.subplots_adjust(left=.12,right=.98,bottom=.24,top=.86,wspace=.38)
ax=axs[0];poly(ax,old,facecolor=BLUE,alpha=.13,edgecolor=BLUE,lw=1,label='原位置域');poly(ax,removed,facecolor=ORANGE,alpha=.5,edgecolor=ORANGE,hatch='////',lw=.6,label='经证书排除');poly(ax,new,facecolor='none',edgecolor=TEAL,lw=1.3,label='保留位置域')
x0,y0,x1,y1=old.bounds;pad=max(x1-x0,y1-y0)*.13;ax.set(xlim=(x0-pad,x1+pad),ylim=(y0-pad,y1+pad),xlabel='$x$ / m',ylabel='$y$ / m',title='(a) 实测历史产生的联合裁剪');style(ax,True);ax.ticklabel_format(useOffset=False,style='plain');ax.locator_params(axis='both',nbins=4)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.005),frameon=False,ncol=3,fontsize=8)
ax=axs[1];rr=np.array([e['new_radius']/e['old_radius'] for e in events]);rr.sort();ax.plot(np.arange(1,len(rr)+1),rr,'o',ms=2.8,c=BLUE);ax.axhline(1,color=GRAY,ls='--',lw=.8)
ax.set(xlabel='裁剪事件（按半径比排序）',ylabel=r'$\rho_{\rm new}/\rho_{\rm old}$',ylim=(0,1.08),title=f'(b) 全部 {len(events)} 次裁剪的半径变化');ax.text(.08,.18,f'{len(reductions)} 次半径下降\n其余事件仅缩小或改变位置域',transform=ax.transAxes,fontsize=8);style(ax)
save(fig,'fig02-joint-domain')


print('All four figures redrawn from evidence only; no API or simulator calls.')
