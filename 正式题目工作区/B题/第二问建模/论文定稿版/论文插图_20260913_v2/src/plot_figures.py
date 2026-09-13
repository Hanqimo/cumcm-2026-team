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

# Same off-centre first point, two bearings; no second-point results are extrapolated.
a0=1200.;betas=[30.,90.];alpha=math.pi/180
nodes,weights=np.polynomial.legendre.leggauss(128)
def cutoff(delta,beta):
 ang=np.deg2rad(beta+np.asarray(delta));return -a0*np.cos(ang)+np.sqrt(1800**2-a0**2*np.sin(ang)**2)
def radial_integral(r):
 r=np.asarray(r);near=(np.minimum(r,1000)**2-25)/2
 far=(1500*(r*r-1000**2)/2-(r**3-1000**3)/3)/500
 return near+np.where(r>1000,far,0)
normalizers={b:float(alpha*np.dot(weights,radial_integral(np.minimum(1500,cutoff(nodes,b))))) for b in betas}
(ROOT/'data/general_posterior_parameters.json').write_text(json.dumps({'a_m':a0,'beta_deg':betas,'C1_m2':normalizers,'central_ray_cutoff_m':{b:float(cutoff(0,b)) for b in betas},'density_units':'per square metre; not per radial-angular coordinate area'},indent=2))
with plt.rc_context(style):
 fig=plt.figure(figsize=(160/25.4,78/25.4),layout='constrained')
 gs=fig.add_gridspec(2,2,width_ratios=[1,1.65],wspace=.10,hspace=.07)
 a=fig.add_subplot(gs[:,0]);axes=[fig.add_subplot(gs[i,1]) for i in range(2)]
 a.add_patch(Circle((0,0),1800,facecolor='#EDF0F2',edgecolor=GRAY,lw=.8))
 for b in betas:
  delta=np.linspace(-1,1,101);end=np.minimum(1500,cutoff(delta,b));ang=np.deg2rad(b+delta)
  pts=np.vstack([[a0+5*math.cos(math.radians(b-1)),5*math.sin(math.radians(b-1))],np.c_[a0+end*np.cos(ang),end*np.sin(ang)],[a0+5*math.cos(math.radians(b+1)),5*math.sin(math.radians(b+1))]])
  a.add_patch(Polygon(pts,facecolor=BLUE,edgecolor=BLUE,lw=.6))
 a.plot(a0,0,'o',color=INK,ms=3,zorder=5);a.annotate(r'$s_1$',(a0,0),xytext=(8,-10),textcoords='offset points',fontsize=10)
 a.text(-1200,700,r'$\Omega$',fontsize=12);a.text(-1400,-1000,'先验：按面积\n均匀分布',fontsize=8)
 a.annotate(r'$\beta=30^\circ$',xy=(1550,200),xytext=(180,-440),arrowprops={'arrowstyle':'-','color':GRAY,'lw':.65},fontsize=8)
 a.annotate(r'$\beta=90^\circ$',xy=(1200,1000),xytext=(-1250,1250),arrowprops={'arrowstyle':'-','color':GRAY,'lw':.65},fontsize=8)
 a.set(xlim=(-2000,2000),ylim=(-2000,2000),xticks=[-1800,0,1800],yticks=[-1800,0,1800],xlabel=r'$x\,/\,\mathrm{m}$',ylabel=r'$y\,/\,\mathrm{m}$');a.set_aspect('equal');decorate(a);panel(a,'(a) 不同示向度对应的区域')
 r=np.linspace(0,1500,1001);ang=np.linspace(-1.2,1.2,241)
 for ax,b,letter in zip(axes,betas,'bc'):
  cut=cutoff(ang,b);weight=np.where(r<=1000,1,np.maximum(0,(1500-r)/500))
  density=np.where((abs(ang[:,None])<=1)&(r[None,:]>5)&(r[None,:]<=cut[:,None]),weight[None,:]/normalizers[b],0)
  np.savez_compressed(ROOT/f'data/posterior_beta_{int(b)}.npz',distance_m=r,relative_angle_deg=ang,density_per_m2=density)
  im=ax.pcolormesh(r,ang,density*1e5,cmap='Blues',vmin=0,vmax=14,shading='nearest',rasterized=True)
  interior=np.linspace(-1,1,201);ax.plot(cutoff(interior,b),interior,color=GRAY,ls='--',lw=.8)
  ax.axhline(-1,color=GRAY,ls=':',lw=.6);ax.axhline(1,color=GRAY,ls=':',lw=.6)
  ax.set(xlim=(0,1500),ylim=(-1.2,1.2),xticks=[0,500,1000,1500],yticks=[-1,0,1],ylabel='相对示向角 / (°)')
  ax.annotate('圆域边界',xy=(float(cutoff(0,b)),0),xytext=(920,.5),arrowprops={'arrowstyle':'-','color':GRAY,'lw':.6},fontsize=7.5)
  if b==90:ax.axvline(1000,color=GRAY,ls=':',lw=.6)
  decorate(ax);panel(ax,f'({letter}) '+rf'$\beta={b:g}^\circ$'+' 时的位置密度')
 axes[-1].set_xlabel(r'源距 $d_1\,/\,\mathrm{m}$');axes[0].tick_params(labelbottom=False)
 cb=fig.colorbar(im,ax=axes,shrink=.86,pad=.025,ticks=[0,4,8,12,14]);cb.set_label(r'$p_1(g)\,/\,(10^{-5}\,\mathrm{m}^{-2})$',labelpad=4);cb.outline.set_linewidth(.6)
 save(fig,'q2_posterior_general')

with plt.rc_context(style):
 fig,a=plt.subplots(figsize=(150/25.4,43/25.4),layout='constrained')
 pro=np.genfromtxt(ROOT/'data/feedback_profile.csv',delimiter=',',names=True);t=pro['theta_deg'];f=pro['pdf_deg'];rho=pro['rho_upper']
 a.plot(t,f,color=BLUE,lw=1.15)
 a.fill_between(t,0,f,where=rho<=20,facecolor='#DCEEE6',edgecolor=GREEN,hatch='////',linewidth=.2)
 for d in [270,300]:a.axvline(d,color=GRAY,ls=':',lw=.8)
 a.set(xlim=(205,328),ylim=(0,.0165),xticks=[210,240,270,300,330],yticks=[0,.005,.010,.015],xlabel=r'第二次示向度 $\theta$ / (°)',ylabel=r'预测密度 / $(^{\circ})^{-1}$')
 a.set_xlim(205,330);decorate(a)
 a.legend(handles=[Line2D([0],[0],color=BLUE,label='正常示向度预测密度'),Patch(facecolor='#DCEEE6',edgecolor=GREEN,hatch='////',label='无需补测的反馈')],loc='upper left',frameon=False,ncols=2,columnspacing=1.2)
 a.text(328,.0155,r'$P_{\mathrm{finish}}=37.34\%$',ha='right',va='top',fontsize=9)
 save(fig,'q2_feedback_distribution')

with plt.rc_context(style):
 fig,bs=plt.subplots(1,2,figsize=(130/25.4,60/25.4),layout='constrained')
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
  panel(ax,f'({"ab"[idx]}) '+rf'$\theta={deg}^\circ$'+('，无需补测' if rr<=20 else '，仍需补测'))
 fig.legend(handles=[Patch(facecolor=PALE,edgecolor=BLUE,label=r'剩余区域 $K_\theta(q)$'),Line2D([0],[0],color=BLUE,label='最小包围圆'),Line2D([0],[0],color=ORANGE,ls='--',label='半径20米的参考圆')],loc='outside lower center',ncols=3,frameon=False,columnspacing=1.8)
 save(fig,'q2_feedback_regions')

(ROOT/'verification/plot_layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2))
