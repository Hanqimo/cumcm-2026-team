"""Three paper figures from evaluated geometry and objective values."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/bq2-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon,Circle,Rectangle,ConnectionPatch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import csv,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=ROOT/'output'
BLUE='#286388';WINE='#a7435a';TEAL='#147d83';ORANGE='#cc7839';INK='#273746';GRAY='#77858c'

def setup():
    for p in ['/System/Library/Fonts/Supplemental/Songti.ttc','/System/Library/Fonts/Supplemental/Times New Roman.ttf']:
        font_manager.fontManager.addfont(p)
    cname=font_manager.FontProperties(fname='/System/Library/Fonts/Supplemental/Songti.ttc').get_name()
    plt.rcParams.update({'font.family':[cname,'Times New Roman'],'font.size':9,'axes.labelsize':9,
        'axes.titlesize':10,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
        'mathtext.fontset':'stix','axes.unicode_minus':False,'axes.spines.top':False,
        'axes.spines.right':False,'axes.linewidth':.65,'xtick.major.width':.6,'ytick.major.width':.6,
        'xtick.major.size':3,'ytick.major.size':3,'text.color':INK,'axes.labelcolor':INK,
        'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':GRAY,
        'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','savefig.facecolor':'white'})

def save(fig,name):
    OUT.mkdir(exist_ok=True)
    for ext in ['pdf','svg','png']:
        fig.savefig(OUT/f'{name}.{ext}',dpi=600,facecolor='white')
    plt.close(fig)

def axis(ax,xlim,ylim):
    ax.set_xlim(xlim);ax.set_ylim(ylim);ax.set_aspect('equal',adjustable='box')
    ax.set_xlabel('$x$（m）',labelpad=2);ax.set_ylabel('$y$（m）',labelpad=2)

def worst_level_boundary(radius):
    # Local 1% boundary from the two controlling support pairs. Both arcs are
    # checked afterwards against the complete continuous-angle minimax solver.
    a=math.pi/180;u0=np.array([math.cos(a),-math.sin(a)]);u1=np.array([math.cos(a),math.sin(a)])
    near_r=5*math.cos(2*a)+math.sqrt(4*radius**2-25*math.sin(2*a)**2)
    c1=near_r*u0;r1=1000.
    far_r=1500*math.cos(2*a)-math.sqrt(4*radius**2-1500**2*math.sin(2*a)**2)
    p=1500*u0;b=far_r*u1;chord=b-p;diam=float(np.linalg.norm(chord))
    perp=np.array([-chord[1],chord[0]])/diam
    c2=(p+b)/2-perp*(diam/(2*math.tan(2*a)));r2=radius/math.sin(2*a)
    u=(c2-c1)/np.linalg.norm(c2-c1);d=float(np.linalg.norm(c2-c1))
    along=(r1*r1-r2*r2+d*d)/(2*d);height=math.sqrt(r1*r1-along*along)
    mid=c1+along*u;normal=np.array([-u[1],u[0]])
    ends=sorted([mid+height*normal,mid-height*normal],key=lambda p:p[0])
    def arc(c,r,start,end):
        t=math.atan2(*(start-c)[::-1]);end_t=math.atan2(*(end-c)[::-1]);delta=math.remainder(end_t-t,2*math.pi)
        angles=np.linspace(t,t+delta,601);return c+r*np.c_[np.cos(angles),np.sin(angles)]
    curve=np.r_[arc(c1,r1,ends[0],ends[1]),arc(c2,r2,ends[1],ends[0])]
    (DATA/'worst_contour_geometry.json').write_text(json.dumps({'threshold_radius_m':radius,'no_signal_circle':{'center':c1.tolist(),'radius':r1},'normal_angle_circle':{'center':c2.tolist(),'radius':r2},'endpoints':[p.tolist() for p in ends]},indent=2))
    return curve

def geometry_figure(g):
    A=math.pi/180;q=np.array(g['q_W']);theta=g['normal_theta']
    polys={k:np.array(v) for k,v in g['polygons'].items()}
    fig=plt.figure(figsize=(7.2,5.45))
    top=fig.add_axes([.09,.565,.83,.375])
    axn=fig.add_axes([.09,.105,.35,.325]);axt=fig.add_axes([.565,.105,.35,.325])
    phi=np.linspace(-A,A,500);unit=np.c_[np.cos(phi),np.sin(phi)]
    first=np.r_[5*unit,1500*unit[::-1]]
    top.add_patch(Polygon(first,facecolor='#e8edef',edgecolor='#839ca8',linewidth=.65,zorder=1))
    for t in [-A,A]:top.plot([0,1500*math.cos(t)],[0,1500*math.sin(t)],color=BLUE,lw=.75)
    second=np.array([q,q+800*np.array([math.cos(theta-A),math.sin(theta-A)]),q+800*np.array([math.cos(theta+A),math.sin(theta+A)])])
    top.add_patch(Polygon(second,facecolor=TEAL,alpha=.07,edgecolor='none'))
    for t in [theta-A,theta+A]:top.plot([q[0],q[0]+800*math.cos(t)],[q[1],q[1]+800*math.sin(t)],color=TEAL,lw=.75,alpha=.9)
    top.plot([q[0],q[0]+770*math.cos(theta)],[q[1],q[1]+770*math.sin(theta)],color=TEAL,lw=.6,ls='--')
    top.add_patch(Circle(q,1000,fill=False,edgecolor=ORANGE,lw=.8,ls=(0,(5,3)),alpha=.65))
    yy=np.array([-50,125]);xx=(float(q@q)/2-q[1]*yy)/q[0]
    top.plot(xx,yy,color=GRAY,lw=.7,ls=':')
    top.text(xx[-1]+12,yy[-1]-5,'$d_2=d_1$',fontsize=8,color=GRAY)
    for kind,c in [('no_signal',ORANGE),('normal',TEAL)]:
        top.add_patch(Polygon(polys[kind],facecolor=c,edgecolor=c,lw=.65,zorder=4))
        cp=g['control'][kind]
        top.add_patch(Circle(cp['center'],cp['radius'],fill=False,edgecolor=c,lw=.9,zorder=3))
    top.plot(0,0,'o',ms=4,color=INK,zorder=8)
    top.annotate('$S_1$',(0,0),xytext=(-11,-15),textcoords='offset points',fontsize=10)
    top.scatter(*q,s=43,marker='D',c=WINE,edgecolors='white',linewidths=.65,zorder=9)
    top.annotate('$q_W$',q,xytext=(8,1),textcoords='offset points',color=WINE,fontsize=10)
    top.annotate('第一次可行区域 $K_1$',xy=(650,0),xytext=(380,240),fontsize=9,
        arrowprops={'arrowstyle':'-','color':GRAY,'lw':.65})
    top.text(80,490,'两次示向度误差均在 ±1° 内',fontsize=8.5,color=GRAY)
    top.annotate('$d_2=1000$ m',xy=(25,170),xytext=(105,270),color=ORANGE,fontsize=8,
        arrowprops={'arrowstyle':'-','color':ORANGE,'lw':.6})
    top.text(1135,335,'第二次方向约束',color=TEAL,fontsize=8.5,rotation=-36)
    top.set_title('（a）检测点与两类反馈区域的整体位置',loc='left',pad=9)
    axis(top,(-70,1580),(-70,555));top.set_xticks([0,500,1000,1500]);top.set_yticks([0,250,500])
    for ax,kind,title,xlim in [(axn,'no_signal','（b）无信号反馈：近端区域',(-10,118)),(axt,'normal','（c）正常示向度反馈：远端区域',(1395,1523))]:
        c=ORANGE if kind=='no_signal' else TEAL;cp=g['control'][kind];center=np.array(cp['center']);rad=cp['radius']
        ax.add_patch(Polygon(first,facecolor='#eff2f3',edgecolor='#b4c2c8',lw=.55))
        ax.add_patch(Polygon(polys[kind],facecolor=c,alpha=.45,edgecolor=c,lw=1.05,zorder=3))
        ax.add_patch(Circle(center,rad,fill=False,ec=c,lw=1.2,ls=(0,(5,2.5)),zorder=4))
        pair=np.array(cp['points']);ax.plot(pair[:,0],pair[:,1],color=c,lw=.65,ls=':',zorder=4)
        ax.scatter(pair[:,0],pair[:,1],s=12,c=c,zorder=5)
        ax.plot(*center,'+',ms=5.5,mew=1,color=INK,zorder=6)
        sub='N' if kind=='no_signal' else r'\theta'
        ax.annotate('$c_{'+sub+'}$',center,xytext=(4,-14),textcoords='offset points',fontsize=9)
        ax.text(center[0],55,'$\\rho_{'+sub+'}=49.04$ m',ha='center',color=c,fontsize=9)
        target=center+np.array([12,0])
        ax.annotate('$K_{'+sub+'}$',xy=target,xytext=(center[0]-30,25) if kind=='no_signal' else (center[0]+10,32),color=c,fontsize=10,
            arrowprops={'arrowstyle':'-','color':c,'lw':.7})
        axis(ax,xlim,(-62,62));ax.set_yticks([-50,0,50]);ax.set_title(title,loc='left',pad=12)
        rect=Rectangle((xlim[0],-58),xlim[1]-xlim[0],116,fill=False,ec=c,lw=.65,ls=(0,(2,3)),alpha=.7)
        top.add_patch(rect)
        fig.add_artist(ConnectionPatch(xyA=(center[0],-64),coordsA=top.transData,xyB=(.5,1.18),coordsB=ax.transAxes,
            color=c,lw=.65,ls=(0,(2,3)),alpha=.6,zorder=0))
    axn.set_xticks([0,50,100]);axt.set_xticks([1400,1450,1500])
    fig.text(.5,.025,'着色区域：反馈后的可行位置集；虚线圆：最小包围圆。各坐标轴均采用等比例尺度。',ha='center',fontsize=8)
    save(fig,'fig01_geometry')

def maps_figure(g,comparison):
    rows=list(csv.DictReader((DATA/'heatmap.csv').open()));xs=sorted({float(r['x']) for r in rows});ys=sorted({float(r['y']) for r in rows})
    x=np.array(xs);y=np.array(ys);X,Y=np.meshgrid(x,y)
    ej=np.array([float(r['expected_radius']) for r in rows]).reshape(len(y),len(x))
    wn=np.array([float(r['normal_lower']) for r in rows]).reshape(len(y),len(x))
    wns=np.array([float(r['no_signal_radius']) for r in rows]).reshape(len(y),len(x))
    wupper=np.array([float(r['worst_upper']) for r in rows]).reshape(len(y),len(x))
    # Interpolate the smooth branches separately before taking their maximum.
    # Interpolating an already-maximized 2 m field cuts across its narrow V-valley.
    fine_x=np.arange(x[0],x[-1]+.01,.25);fine_y=np.arange(y[0],y[-1]+.01,.25)
    def interpolate(z):
        tmp=np.array([np.interp(fine_x,x,row) for row in z])
        return np.array([np.interp(fine_y,y,tmp[:,j]) for j in range(len(fine_x))]).T
    wj=np.maximum(interpolate(wn),interpolate(wns))+interpolate(np.maximum(0,wupper-np.maximum(wn,wns)))
    FX,FY=np.meshgrid(fine_x,fine_y)
    refs=[comparison['results']['expected']['uniform_prior_expectation']['E_radius_loss'],comparison['results']['minimax']['strict_worst']['worst_upper']]
    rels=[100*(ej/refs[0]-1),100*(wj/refs[1]-1)]
    cmap=LinearSegmentedColormap.from_list('q2', ['#f7fbf9','#d9ece8','#97c9c6','#4e99ab','#265b79','#18364f'])
    fig,axes=plt.subplots(1,2,figsize=(7.2,4.95),sharex=True,sharey=True)
    fig.subplots_adjust(left=.09,right=.845,bottom=.235,top=.86,wspace=.18)
    contours={}
    for i,(ax,z,title,ref) in enumerate(zip(axes,rels,['（a）期望半径 $J_R(q)$','（b）最坏半径 $W(q)$'],refs)):
        gx,gy=(X,Y) if i==0 else (FX,FY)
        cf=ax.contourf(gx,gy,np.maximum(0,z),levels=np.linspace(0,10,41),cmap=cmap,extend='max')
        if i==0:
            cs=ax.contour(gx,gy,z,levels=[1],colors=['#ad563a'],linewidths=1.05)
            contours['expected']=[v.tolist() for v in cs.allsegs[0] if len(v)>1]
        else:
            curve=worst_level_boundary(ref*1.01)
            ax.plot(curve[:,0],curve[:,1],color='#ad563a',lw=1.05)
            contours['worst']=[curve.tolist()]
        qe=np.array(g['q_E']);qw=np.array(g['q_W'])
        ax.scatter(*qe,s=95,marker='*',c=BLUE,edgecolors='white',linewidths=.65,zorder=5)
        ax.scatter(*qw,s=35,marker='D',c=WINE,edgecolors='white',linewidths=.65,zorder=5)
        ax.annotate('$q_E$',qe,xytext=(7,5),textcoords='offset points',color=BLUE,fontsize=10,bbox={'fc':'white','ec':'none','alpha':.85,'pad':1})
        ax.annotate('$q_W$',qw,xytext=(7,-12),textcoords='offset points',color=WINE,fontsize=10,bbox={'fc':'white','ec':'none','alpha':.85,'pad':1})
        ax.set_title(title,pad=26,loc='left')
        ax.text(0,1.025,f'最优方案半径：{ref:.5f} m',transform=ax.transAxes,fontsize=8.2,color=GRAY)
        ax.set_aspect('equal');ax.set_xlim(800,1040);ax.set_ylim(400,700)
        ax.set_xticks([800,880,960,1040]);ax.set_yticks([400,450,500,550,600,650,700])
        ax.set_xlabel('$q_x$（m）')
    axes[0].set_ylabel('$q_y$（m）')
    cbax=fig.add_axes([.878,.26,.025,.535]);cb=fig.colorbar(cf,cax=cbax,ticks=[0,1,2,4,6,8,10])
    cb.set_label('相对各自最优方案的增幅（%）',labelpad=8,fontsize=8.5);cb.outline.set_linewidth(.5)
    handles=[Line2D([],[],marker='*',markersize=9,color='none',markerfacecolor=BLUE,markeredgecolor='white',label='期望最优点 $q_E$'),
             Line2D([],[],marker='D',markersize=5,color='none',markerfacecolor=WINE,markeredgecolor='white',label='最坏近优点 $q_W$'),
             Line2D([],[],color='#ad563a',lw=1.1,label='1% 近优边界')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.48,.084),ncol=3,frameon=False,columnspacing=1.6,handletextpad=.55)
    fig.text(.47,.027,'仅展示北侧局部区域；超过 10% 的增幅采用最高色阶，南侧由反射对称得到。',ha='center',fontsize=8)
    (DATA/'contours_1pct.json').write_text(json.dumps(contours,indent=2))
    save(fig,'fig02_objective_maps')

def balance_figure(g):
    rows=list(csv.DictReader((DATA/'branch_curve.csv').open()))
    t=np.array([float(r['t']) for r in rows]);normal=np.array([float(r['normal_lower']) for r in rows]);ns=np.array([float(r['no_signal_radius']) for r in rows]);worst=np.array([float(r['worst_upper']) for r in rows])
    fig,ax=plt.subplots(figsize=(7.2,3.85));fig.subplots_adjust(left=.105,right=.97,bottom=.22,top=.92)
    ax.plot(t,worst,color=INK,lw=3.3,label='总最坏半径 $W$',zorder=2)
    ax.plot(t,normal,color=TEAL,lw=1.4,label='正常示向度的最坏半径',zorder=3)
    ax.plot(t,ns,color=ORANGE,lw=1.5,ls=(0,(5,2.5)),label='无信号分支半径',zorder=3)
    for tx,c,lab in [(0,BLUE,'$q_E$'),(1,WINE,'$q_W$')]:
        j=int(np.argmin(abs(t-tx)));ax.scatter(tx,worst[j],s=58 if tx==0 else 34,marker='*' if tx==0 else 'D',color=c,edgecolors='white',linewidths=.6,zorder=8)
        ax.plot([tx,tx],[worst[j]+.35,55.4],color=c,lw=.65,ls=':',alpha=.6,zorder=0)
        ax.text(tx,55.55,lab,color=c,ha='center',fontsize=10)
    ax.annotate('期望最优点\n最坏半径 50.38 m',xy=(0,worst[np.argmin(abs(t))]),xytext=(-.18,53.55),
        fontsize=8.7,color=BLUE,arrowprops={'arrowstyle':'-','color':BLUE,'lw':.7},ha='left')
    ax.annotate('两类反馈损失接近平衡\n最坏半径 49.04 m',xy=(1,worst[np.argmin(abs(t-1))]),xytext=(.42,53.0),
        fontsize=8.7,color=WINE,arrowprops={'arrowstyle':'-','color':WINE,'lw':.7},ha='left')
    ax.set_xlim(-.25,1.3);ax.set_ylim(37,56.2);ax.set_xticks([-.25,0,.25,.5,.75,1,1.25]);ax.set_yticks([40,45,50,55])
    ax.set_ylabel('剩余包围圆半径（m）');ax.set_xlabel('检测点位置参数 $t$，$q(t)=q_E+t(q_W-q_E)$',labelpad=7)
    ax.grid(axis='y',color='#e4e9eb',lw=.55,zorder=0)
    handles,labels=ax.get_legend_handles_labels();order=[1,2,0]
    ax.legend([handles[i] for i in order],[labels[i] for i in order],loc='lower right',frameon=False,fontsize=8.4)
    fig.text(.53,.055,'沿两方案连线逐点计算；黑色上包络为两类非终止反馈损失的最大值。',ha='center',fontsize=8)
    save(fig,'fig03_branch_balance')

def main():
    setup();g=json.loads((DATA/'geometry.json').read_text());comparison=json.loads((ROOT.parent/'worstcase/runs/R001/comparison.json').read_text())
    geometry_figure(g);maps_figure(g,comparison);balance_figure(g)
    print('Wrote three figures in PDF, SVG and 600-dpi PNG.')
if __name__=='__main__':main()
