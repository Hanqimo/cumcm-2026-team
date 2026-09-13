from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon,Rectangle
from shapely import wkt

BASE=Path(__file__).resolve().parent/'data'
OUT=Path(__file__).resolve().parent/'figures'
OUT.mkdir(exist_ok=True)
case={'case_code':'T446-VHAY-76FH-9VYW'}
log=BASE/'optical_events.jsonl'
events=[json.loads(x) for x in log.read_text(encoding='utf-8').splitlines()]
i=next(i for i,e in enumerate(events) if e['kind']=='optical_failure_update')
failed=events[i];ch=failed['channel']
before=next(e for e in reversed(events[:i]) if e['kind']=='optical_region' and e['channel']==ch)
after=next(e for e in events[i+1:] if e['kind']=='optical_region' and e['channel']==ch)
meta=json.loads((BASE/'optical_example.json').read_text(encoding='utf-8'))
origin=np.array(meta['origin']);rot=np.array(meta['rotation_columns'])
clear=meta['clear_certificate']
BLUE,TEAL,ORANGE,GRAY,RED='#245B83','#26756B','#B46A24','#64717C','#A54246'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['SimSun','DejaVu Sans'],
 'mathtext.fontset':'stix','font.size':9,'axes.labelsize':9,'axes.titlesize':9.5,
 'xtick.labelsize':8,'ytick.labelsize':8,'axes.linewidth':.65,
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.unicode_minus':False,
 'savefig.facecolor':'white','figure.facecolor':'white'})
def xy(a):return (np.array(a)-origin)@rot
def region(ax,record,color,alpha):
    geom=wkt.loads(record['wkt'])
    for g in getattr(geom,'geoms',[geom]):
        ax.add_patch(Polygon(xy(g.exterior.coords),fc=color,ec=color,lw=.7,alpha=alpha))
def layers(ax,k):
    if k==0:
        region(ax,before,BLUE,.25);region(ax,failed,TEAL,.65)
        ax.add_patch(Circle((0,0),20,fc=ORANGE,ec=ORANGE,alpha=.18,lw=.8,ls='--'))
    else:
        region(ax,failed,GRAY,.18);region(ax,after,BLUE,.6)
        ax.add_patch(Circle(xy(clear['point']),19.5,fill=False,ec=TEAL,lw=.9,ls='--'))
fig,axes=plt.subplots(1,2,figsize=(160/25.4,65/25.4))
fig.subplots_adjust(left=.085,right=.985,bottom=.25,top=.86,wspace=.28)
for k,ax in enumerate(axes):
    layers(ax,k)
    ax.set(aspect='equal',xlim=(-98,98),ylim=(-48,48),xlabel=r"$x'\,/\mathrm{m}$",ylabel=r"$y'\,/\mathrm{m}$")
    ax.set_xticks([-80,-40,0,40,80]);ax.set_yticks([-40,0,40]);ax.grid(alpha=.15,lw=.5)
    ax.add_patch(Rectangle((-26,-1),10,5,fill=False,ec=RED,lw=.7))
    ins=ax.inset_axes([.54,.10,.43,.30]);layers(ins,k)
    ins.set(aspect='equal',xlim=(-26,-16),ylim=(-1,4))
    ins.set_xticks([-25,-20]);ins.set_yticks([0,3]);ins.tick_params(labelsize=6,pad=1,length=2)
    ins.set_title('红框局部放大（等比例）',fontsize=6.1,pad=1)
    for spine in ins.spines.values():spine.set_color(RED);spine.set_linewidth(.65)
    ax.plot([-16,0],[1.5,-16],color=RED,lw=.55,ls=':')
axes[0].scatter([0],[0],s=25,marker='x',c=RED,zorder=5)
axes[0].annotate('试清位置',(0,0),(16,32),fontsize=8,arrowprops={'arrowstyle':'-','color':GRAY,'lw':.6})
axes[0].set_title('(a) 试清失败后保留两部分区域',loc='left',pad=9)
cq=xy(clear['point']);axes[1].scatter(*cq,s=35,marker='*',c=TEAL,zorder=6)
axes[1].scatter([0],[0],s=20,facecolors='white',edgecolors=BLUE,zorder=5)
axes[1].annotate('可靠清除位置',cq,(-75,32),fontsize=8,arrowprops={'arrowstyle':'-','color':GRAY,'lw':.6})
axes[1].set_title('(b) 再测向后进入可靠清除范围',loc='left',pad=9)
fig.text(.5,.075,'主图与插窗分别保持等比例；插窗刻度单位为米',ha='center',fontsize=8)
for ext in ['pdf','svg','png']:fig.savefig(OUT/f'q3-optical.{ext}',dpi=400)
plt.close(fig)
report={'input_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'case':case['case_code'],
 'channel':ch,'transform':'rigid translation and rotation only','main_aspect':'equal',
 'inset_aspect':'equal','inset_xlim':[-26,-16],'inset_ylim':[-1,4],
 'outputs':{ext:hashlib.sha256((OUT/f'q3-optical.{ext}').read_bytes()).hexdigest() for ext in ['pdf','svg','png']}}
(Path(__file__).parent/'optical_revision_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(report)
