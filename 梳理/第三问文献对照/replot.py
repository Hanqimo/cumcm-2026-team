from pathlib import Path
import json
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

HERE=Path(__file__).resolve().parent
OUT=HERE/'figures';OUT.mkdir(exist_ok=True)
PAIR=HERE/'paired'
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False})
colors=['#AD5B00','#777777','#176B9B']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(fig,name):
    for ext in ['pdf','svg','png']:
        fig.savefig(OUT/(name+'.'+ext),dpi=360,facecolor='white')
    plt.close(fig)

a=read(PAIR/'baseline/results.json');b=read(PAIR/'v6/results.json')
assert len(a)==len(b)==30 and all(x['full'] for x in a+b)
delta=np.array([x['per_source_s']-y['per_source_s'] for x,y in zip(a,b)])
i=min(range(30),key=lambda j:(abs(delta[j]-np.median(delta)),a[j]['seed']))
seed=a[i]['seed'];assert seed==b[i]['seed']
fixture=read(PAIR/'baseline/fixtures.json')[i]
fig,axs=plt.subplots(1,2,figsize=(160/25.4,87/25.4))
fig.subplots_adjust(left=.10,right=.98,top=.79,bottom=.20,wspace=.28)
fig.suptitle(f'同场景本地对照 · 种子 {seed} · {fixture["n"]} 个源',y=.99,fontsize=8)
for ax,key,row,color,title in zip(axs,['baseline','v6'],[a[i],b[i]],[colors[0],colors[2]],['(a) 文献适配基线：逐源处理','(b) v6：联合安排任务']):
    events=read(PAIR/key/f'{seed}-actions.json')['actions']
    points=np.vstack([[0,0],[e['point'] for e in events]])/1000
    points=points[np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-7]]
    ax.add_patch(Circle((0,0),1.8,fill=False,color='#777777',lw=.7,linestyle='--'))
    ax.plot(points[:,0],points[:,1],color=color,lw=.7,alpha=.8,zorder=2)
    # Arrow every fourth nonzero leg, all actual legs remain visible.
    for j in range(0,len(points)-1,4):
        p,q=points[j],points[j+1];mid=(p+q)/2
        ax.annotate('',xy=mid+.045*(q-p)/np.linalg.norm(q-p),xytext=mid-.045*(q-p)/np.linalg.norm(q-p),arrowprops=dict(arrowstyle='->',color=color,lw=.8,mutation_scale=6))
    source=np.array([s['point'] for s in fixture['sources'].values()])/1000
    ax.scatter(source[:,0],source[:,1],marker='x',s=15,c='#222222',lw=.65,zorder=4)
    counts=Counter(tuple(np.round(e['point'],4)) for e in events if e['kind']=='measure')
    sites=np.array([p for p,n in counts.items() if n>=4])/1000
    if len(sites):ax.scatter(sites[:,0],sites[:,1],s=30,facecolors='white',edgecolors=color,lw=1,zorder=5)
    ax.scatter([0],[0],s=28,marker='s',c='black',zorder=6)
    ax.set(xlim=(-1.95,1.95),ylim=(-1.95,1.95),xticks=[-1.5,0,1.5],yticks=[-1.5,0,1.5],xlabel='x / km',ylabel='y / km')
    ax.set_aspect('equal');ax.grid(alpha=.15,lw=.5)
    ax.set_title(title,pad=23,loc='left')
    ax.text(.5,1.025,f"{row['distance_m']/1000:.2f} km · {row['measures']} 次检测 · {row['time_s']:.1f} s",ha='center',transform=ax.transAxes,fontsize=7)
fig.legend(handles=[Line2D([],[],c='#666666',lw=.8,label='实际移动路线'),Line2D([],[],c='black',marker='x',ls='',label='源真值（仅事后绘图）'),Line2D([],[],c='#666666',marker='o',mfc='white',ls='',label='同点至少 4 次检测'),Line2D([],[],c='black',marker='s',ls='',label='起点')],loc='lower center',bbox_to_anchor=(.5,.04),ncol=2,frameon=False,fontsize=7,columnspacing=1.6)
save(fig,'q3-route-coverage')

if not (HERE/'data/analysis.json').exists():
    print('Paired route complete; official plots wait for all 30 results.');raise SystemExit(0)
groups=read(HERE/'data/official_groups.json');report=read(HERE/'data/analysis.json')
fig,axs=plt.subplots(1,2,figsize=(160/25.4,78/25.4),gridspec_kw={'width_ratios':[1,1.15]})
fig.subplots_adjust(left=.105,right=.975,bottom=.22,top=.85,wspace=.37)
ax=axs[0];rng=np.random.default_rng(20260913)
names=['文献适配\n30 场','v4\n50 场','v6\n50 场']
for j,(key,col) in enumerate(zip(['literature','v4','v6'],colors)):
    values=[r['per_source_s'] for r in groups[key] if r['full']]
    ax.scatter(j+rng.uniform(-.16,.16,len(values)),values,c=col,s=8,alpha=.5,linewidths=0)
    s=report['official'][key];ax.errorbar(j,s['mean'],yerr=np.array([[s['mean']-s['sem_ci95'][0]],[s['sem_ci95'][1]-s['mean']]]),fmt='D',ms=4,c='black',capsize=3,lw=1,zorder=5)
ax.set(xticks=range(3),xticklabels=names,ylabel='场均每源耗时 / s',ylim=(0,450),xlim=(-.5,2.5))
ax.set_title('(a) 独立官方演练：保留每场观测',loc='left',pad=13)
ax.yaxis.grid(alpha=.2,lw=.5)
ax.text(.02,.98,'◆ 均值及 95% 均值置信区间',transform=ax.transAxes,va='top',fontsize=6.7)
ax=axs[1];cost_colors=['#176B9B','#D9902B','#707070','#37816A','#B8475B'];labels=['移动','检测','换频','成功清除','失败清除'];hatches=['','///','...','xx','\\\\']
for j,key in enumerate(['literature','v4','v6']):
    left=0
    for k,value in enumerate(report['official'][key]['cost']):
        ax.barh(j,value,left=left,color=cost_colors[k],height=.55,label=labels[k] if j==0 else None,hatch=hatches[k],edgecolor='white',lw=.35)
        if k<2:ax.text(left+value/2,j,f'{value:.1f}',ha='center',va='center',fontsize=7,color='white' if k==0 else 'black')
        left+=value
    ax.text(left+4,j,f'{left:.1f}',va='center',fontsize=7)
ax.set(yticks=range(3),yticklabels=['文献适配','v4','v6'],xlabel='各场先除以源数，再平均 / s',xlim=(0,380),ylim=(2.55,-.65))
ax.set_title('(b) 节省来自哪些费用',loc='left',pad=13);ax.xaxis.grid(alpha=.15,lw=.5)
ax.legend(loc='lower center',bbox_to_anchor=(.75,.005),bbox_transform=fig.transFigure,ncol=3,frameon=False,fontsize=6.5,columnspacing=1,handlelength=1.3)
save(fig,'q3-performance')
print('Saved official comparison and paired local route figures.')
