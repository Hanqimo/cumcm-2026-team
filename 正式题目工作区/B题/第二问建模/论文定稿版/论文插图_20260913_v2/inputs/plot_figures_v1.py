"""Three Chinese manuscript figures, 160 mm wide, no overall in-image titles."""
from pathlib import Path
import sys, os, json, csv, math, warnings
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/q2-paperfig-mpl')
try: import matplotlib
except ImportError:
 sys.path.insert(0,'/private/tmp/bq2-plot-deps');import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager, colors
from matplotlib.patches import Circle, Wedge, Polygon, Patch
from matplotlib.lines import Line2D
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
font='/Applications/Microsoft Word.app/Contents/Resources/DFonts/SimHei.ttf'
font_manager.fontManager.addfont(font)
BLUE='#0072B2';ORANGE='#D55E00';GREEN='#00865E';INK='#20252B';GRAY='#78828B';PALE='#E5F0F6'
style={'font.family':'SimHei','font.size':8.5,'axes.labelsize':9,'axes.titlesize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'mathtext.fontset':'stix','axes.unicode_minus':False,'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':GRAY,'axes.linewidth':.65,'lines.linewidth':1.1,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'path','savefig.facecolor':'white','figure.facecolor':'white','hatch.linewidth':.45}
report={}
def decorate(ax,grid=False):
 ax.spines[['top','right']].set_visible(False)
 ax.tick_params(direction='out',length=2.5,width=.65)
 if grid:ax.grid(color='#E4E8EB',linewidth=.5,zorder=0)
def panel(ax,text):ax.set_title(text,loc='left',pad=6)
def save(fig,name):
 fig.canvas.draw()
 renderer=fig.canvas.get_renderer();outer=fig.bbox;out=[]
 for obj in fig.findobj(matplotlib.text.Text):
  if not obj.get_visible() or not obj.get_text():continue
  b=obj.get_window_extent(renderer)
  if b.x0<-.5 or b.y0<-.5 or b.x1>outer.width+.5 or b.y1>outer.height+.5:out.append(obj.get_text())
 assert not out,(name,out)
 for ext in ['pdf','svg','png']:
  fig.savefig(ROOT/f'figures/{name}.{ext}',dpi=600,facecolor='white',transparent=False)
 # Preserve opaque RGB, retain actual DPI; vector PDF/SVG remain unchanged.
 p=ROOT/f'figures/{name}.png'
 with Image.open(p) as im:im.convert('RGB').save(p,dpi=(600,600))
 with Image.open(p) as im:
  im.thumbnail((1500,1500));im.save(ROOT/f'verification/{name}_preview.png')
  im.convert('L').save(ROOT/f'verification/{name}_grayscale.png')
 report[name]={'width_mm':float(fig.get_figwidth()*25.4),'height_mm':float(fig.get_figheight()*25.4),'out_of_canvas_text':out,'overall_title':False}
 plt.close(fig)
C1=json.loads((ROOT/'verification/numerical_checks.json').read_text())['C1_analytic_m2']
rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((ROOT/'inputs/candidates.csv').open())]
with plt.rc_context(style):
 fig=plt.figure(figsize=(160/25.4,70/25.4),layout='constrained')
 gs=fig.add_gridspec(1,2,width_ratios=[1,1.7],wspace=.09)
 a=fig.add_subplot(gs[0,0]);b=fig.add_subplot(gs[0,1])
 a.add_patch(Circle((0,0),1800,facecolor='#EDF0F2',edgecolor=GRAY,lw=.8))
 a.add_patch(Wedge((0,0),1500,-1,1,width=1495,facecolor=BLUE,edgecolor=BLUE,lw=.6))
 a.plot(0,0,'o',color=INK,ms=3,zorder=5);a.annotate(r'$s_1$',(0,0),xytext=(-13,8),textcoords='offset points')
 a.text(-1100,650,r'$\Omega$',fontsize=12)
 a.text(-1400,-1050,'先验：按面积\n均匀分布',fontsize=8)
 a.annotate(r'$K_1$',xy=(1100,0),xytext=(1050,900),arrowprops={'arrowstyle':'-','color':INK,'lw':.65},fontsize=11)
 a.set(xlim=(-2000,2000),ylim=(-2000,2000),xticks=[-1800,0,1800],yticks=[-1800,0,1800],xlabel=r'$x\,/\,\mathrm{m}$',ylabel=r'$y\,/\,\mathrm{m}$');a.set_aspect('equal');decorate(a)
 panel(a,'(a) 初始圆域与首次可行区域')
 # The displayed color is density per square metre, NOT density with respect to dr d(angle).
 r=np.linspace(0,1500,901);ang=np.linspace(-1.2,1.2,241)
 weight=np.where(r<=1000,1,np.maximum(0,(1500-r)/500));density=np.where((abs(ang[:,None])<=1)&(r[None,:]>5),weight[None,:]/C1,0)
 np.savez_compressed(ROOT/'data/posterior_grid.npz',distance_m=r,relative_angle_deg=ang,density_per_m2=density)
 image=b.pcolormesh(r,ang,density*1e5,cmap='Blues',vmin=0,vmax=4,shading='nearest',rasterized=True)
 b.axvline(1000,color=INK,lw=.7,ls='--');b.axhline(-1,color=GRAY,lw=.7,ls=':');b.axhline(1,color=GRAY,lw=.7,ls=':')
 b.set(xlim=(0,1500),ylim=(-1.2,1.2),xticks=[0,500,1000,1500],yticks=[-1,0,1],xlabel=r'源距 $d_1\,/\,\mathrm{m}$',ylabel='相对示向角 / (°)')
 decorate(b);panel(b,'(b) 首次观测后的位置密度')
 cb=fig.colorbar(image,ax=b,shrink=.84,pad=.025,ticks=[0,1,2,3,4]);cb.set_label(r'$p_1(g)\,/\,(10^{-5}\,\mathrm{m}^{-2})$',labelpad=5);cb.outline.set_linewidth(.6)
 save(fig,'q2_posterior')

with plt.rc_context(style):
 fig=plt.figure(figsize=(160/25.4,110/25.4),layout='constrained')
 gs=fig.add_gridspec(2,2,height_ratios=[.9,1.1],hspace=.05,wspace=.07)
 a=fig.add_subplot(gs[0,:]);bs=[fig.add_subplot(gs[1,0]),fig.add_subplot(gs[1,1])]
 pro=np.genfromtxt(ROOT/'data/feedback_profile.csv',delimiter=',',names=True);t=pro['theta_deg'];f=pro['pdf_deg'];rho=pro['rho_upper']
 a.plot(t,f,color=BLUE,lw=1.15)
 a.fill_between(t,0,f,where=rho<=20,facecolor='#DCEEE6',edgecolor=GREEN,hatch='////',linewidth=.2)
 for d in [270,300]:a.axvline(d,color=GRAY,ls=':',lw=.8)
 a.set(xlim=(205,328),ylim=(0,.0165),xticks=[210,240,270,300,330],yticks=[0,.005,.010,.015],xlabel=r'第二次示向度 $\theta$ / (°)',ylabel=r'预测密度 / $(^{\circ})^{-1}$')
 a.set_xlim(205,330);decorate(a)
 a.legend(handles=[Line2D([0],[0],color=BLUE,label='正常示向度预测密度'),Patch(facecolor='#DCEEE6',edgecolor=GREEN,hatch='////',label='无需补测的反馈')],loc='upper left',frameon=False,ncols=2,columnspacing=1.2)
 panel(a,'(a) 可能反馈及其完成条件')
 a.text(328,.0155,r'$P_{\mathrm{finish}}=37.34\%$',ha='right',va='top',fontsize=9)
 for idx,(ax,deg) in enumerate(zip(bs,[270,300])):
  geo=json.loads((ROOT/f'data/geometry_{deg}.json').read_text());v=np.array(geo['points']);c=np.array(geo['center']);rr=geo['radius_upper']
  points=[*v]
  for x,y,r,l,h in geo['arcs']:
   n=max(2,math.ceil((h-l)/max(1e-8,2*math.acos(1-1e-4/r))))
   angle=np.linspace(l,h,n+1);points.extend(np.c_[x+r*np.cos(angle),y+r*np.sin(angle)])
  points=np.array(points);mid=points.mean(0);points=points[np.argsort(np.arctan2(points[:,1]-mid[1],points[:,0]-mid[0]))]
  np.savetxt(ROOT/f'data/boundary_{deg}.csv',points,delimiter=',',header='x_m,y_m',comments='')
  ax.add_patch(Polygon(points,facecolor=PALE,edgecolor=BLUE,lw=1,zorder=2))
  ax.add_patch(Circle(c,rr,facecolor='none',edgecolor=BLUE,lw=1.1,zorder=3))
  ax.add_patch(Circle(c,20,facecolor='none',edgecolor=ORANGE,ls='--',lw=1.1,zorder=4))
  ax.plot(*c,'o',color=INK,ms=2.5,zorder=5)
  ax.annotate('圆心',xy=c,xytext=(5,-11),textcoords='offset points',fontsize=7.5)
  ax.set(xlim=(c[0]-40,c[0]+40),ylim=(c[1]-39,c[1]+41),xlabel=r'$x\,/\,\mathrm{m}$',ylabel=r'$y\,/\,\mathrm{m}$');ax.set_aspect('equal')
  # Plot global coordinates with common 80 m spans and 20 m tick spacing.
  ax.set_xticks(np.arange(math.ceil((c[0]-40)/20)*20,c[0]+40,20));ax.set_yticks(np.arange(math.ceil((c[1]-39)/20)*20,c[1]+41,20))
  decorate(ax)
  ax.text(.025,.95,rf'$\rho_\theta={rr:.2f}\,\mathrm{{m}}$',transform=ax.transAxes,va='top',fontsize=8.5)
  panel(ax,f'({"bc"[idx]}) '+rf'$\theta={deg}^\circ$'+('，无需补测' if rr<=20 else '，仍需补测'))
 fig.legend(handles=[Patch(facecolor=PALE,edgecolor=BLUE,label=r'剩余区域 $K_\theta(q)$'),Line2D([0],[0],color=BLUE,label='最小包围圆'),Line2D([0],[0],color=ORANGE,ls='--',label='半径20米的参考圆')],loc='outside lower center',ncols=3,frameon=False,columnspacing=1.8)
 save(fig,'q2_feedback')

with plt.rc_context(style):
 fig=plt.figure(figsize=(160/25.4,80/25.4),layout='constrained')
 gs=fig.add_gridspec(1,2,width_ratios=[1.13,1],wspace=.08)
 a=fig.add_subplot(gs[0,0]);b=fig.add_subplot(gs[0,1]);w=np.array([r['w'] for r in rows]);x=np.array([r['x_global'] for r in rows]);y=np.array([r['y_global'] for r in rows]);J=np.array([r['J'] for r in rows]);P=np.array([r['P_finish'] for r in rows])*100
 cmap=colors.LinearSegmentedColormap.from_list('weight_blues',plt.get_cmap('Blues')(np.linspace(.38,.95,256)));norm=colors.Normalize(0,1)
 a.add_patch(Wedge((0,0),1500,-1,1,width=1495,facecolor=PALE,edgecolor=GRAY,lw=.65))
 a.axhline(0,color='#B8C1C8',ls=':',lw=.6,zorder=0)
 a.plot(0,0,'o',color=INK,ms=3,zorder=5);a.annotate(r'$s_1$',(0,0),xytext=(1,-15),textcoords='offset points',fontsize=10)
 a.annotate(r'$K_1$',(1210,0),xytext=(1150,145),arrowprops={'arrowstyle':'-','color':INK,'lw':.6},fontsize=11)
 for sign in [1,-1]:
  a.plot(x,sign*y,color='#8C9BA6',ls='--',lw=.7,zorder=1)
  a.scatter(x,sign*y,c=w,cmap=cmap,norm=norm,s=19,edgecolors=INK,linewidths=.35,zorder=3)
 # Label both endpoint weights and a representative intermediate weight without covering points.
 for idx,off,ha in [(0,(9,2),'left'),(5,(-28,7),'right'),(10,(-9,-7),'right')]:
  a.annotate(rf'$w={w[idx]:g}$',(x[idx],y[idx]),xytext=off,textcoords='offset points',ha=ha,fontsize=8,arrowprops={'arrowstyle':'-','lw':.55,'color':GRAY})
 a.text(940,-500,'对称候选点',fontsize=8,ha='left')
 a.set(xlim=(-120,1550),ylim=(-730,790),xticks=[0,500,1000,1500],yticks=[-500,0,500],xlabel=r'$x\,/\,\mathrm{m}$',ylabel=r'$y\,/\,\mathrm{m}$');a.set_aspect('equal');decorate(a);panel(a,'(a) 不同权重下的候选位置')
 b.plot(J,P,color='#8C9BA6',ls='--',lw=.7,zorder=1);b.scatter(J,P,c=w,cmap=cmap,norm=norm,s=26,edgecolors=INK,linewidths=.4,zorder=3)
 for idx,off,ha in [(0,(8,-4),'left'),(5,(-6,11),'right'),(10,(-3,-16),'right')]:
  b.annotate(rf'$w={w[idx]:g}$',(J[idx],P[idx]),xytext=off,textcoords='offset points',ha=ha,fontsize=8)
 b.set(xlim=(24.85,28.35),ylim=(24,43),xticks=[25,26,27,28],yticks=[25,30,35,40],xlabel=r'期望定位损失 $J\,/\,\mathrm{m}$',ylabel=r'完成概率 $P_{\mathrm{finish}}$ / %');decorate(b,True);panel(b,'(b) 期望损失与完成概率的权衡')
 cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap),ax=[a,b],location='bottom',shrink=.55,aspect=38,pad=.08,ticks=[0,.5,1]);cb.set_label(r'完成概率权重 $w$',labelpad=1);cb.outline.set_linewidth(.6)
 save(fig,'q2_candidates')
(ROOT/'verification/plot_layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2))
