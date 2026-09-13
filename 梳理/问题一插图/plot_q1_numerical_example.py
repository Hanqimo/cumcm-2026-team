"""第一问数值计算示例的局部几何图；读取原始全精度顶点，保存 PDF、PNG 和清单。
Run: python3 梳理/问题一插图/plot_q1_numerical_example.py
Dependencies: numpy, matplotlib. Optionally set CJK_FONT to a Chinese font file.
"""
from pathlib import Path
import hashlib,json,os
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.patches import Polygon,Circle,Patch
from matplotlib.lines import Line2D

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[1]
SOURCE=REPO/'contest/q1/models/m01-bounded-bearing/runs/R003/orthogonal_example.json'
data=json.loads(SOURCE.read_text());v=np.array(data['vertices']);c=np.array(data['cover_center']);r=data['cover_radius_m'];diameter=data['diameter_m'];i,j=data['diameter_pair']
assert [i,j]==[0,2]
assert np.max(np.linalg.norm(v-c,axis=1))<=r+1e-8
assert np.linalg.norm((v[i]+v[j])/2-c)<1e-8 and abs(2*r-diameter)<1e-8
assert r>20
slope=np.tan(np.deg2rad(1.));residual=max(np.max(np.abs(v[:,1])-(v[:,0]+1000)*slope),np.max(np.abs(v[:,0])-(v[:,1]+1000)*slope))
assert residual<1e-8
candidates=[os.environ.get('CJK_FONT',''),'/Applications/Microsoft Word.app/Contents/Resources/DFonts/SimHei.ttf','/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
font=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
if font is None:raise RuntimeError('请通过 CJK_FONT 指定中文字体文件。')
font_manager.fontManager.addfont(str(font));family=font_manager.FontProperties(fname=str(font)).get_name()
BLUE,GOLD,INK,GRAY='#356C91','#A97A26','#253746','#8F969A'
style={'font.family':family,'font.size':10,'mathtext.fontset':'stix','axes.unicode_minus':False,'pdf.fonttype':42,'ps.fonttype':42,
       'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'axes.edgecolor':'#A5ADB2','axes.linewidth':.6,
       'figure.facecolor':'white','savefig.facecolor':'white'}
with plt.rc_context(style):
    fig,ax=plt.subplots(figsize=(110/25.4,85/25.4))
    fig.subplots_adjust(left=.14,right=.96,bottom=.30,top=.985)
    ax.set_aspect('equal');ax.set(xlim=(-32,32),ylim=(-32,32),xticks=[-20,0,20],yticks=[-20,0,20],xlabel=r'$x_g\,/\,\mathrm{m}$',ylabel=r'$y_g\,/\,\mathrm{m}$')
    ax.tick_params(labelsize=9,length=3,pad=2)
    q=np.linspace(-32,32,200)
    for sign in [-1,1]:
        ax.plot(q,sign*(q+1000)*slope,color=GRAY,lw=.9,ls=':',zorder=1)
        ax.plot(sign*(q+1000)*slope,q,color=GRAY,lw=.9,ls=':',zorder=1)
    ax.add_patch(Polygon(v,facecolor='#DCEAF2',edgecolor=BLUE,lw=1.1,zorder=2))
    ax.add_patch(Circle(c,r,fill=False,edgecolor=BLUE,lw=1.6,zorder=3))
    ax.plot(*v[[i,j]].T,color=GOLD,lw=1.4,ls=(0,(5,3)),zorder=4)
    ax.annotate('',xy=c+[0,r],xytext=c,arrowprops={'arrowstyle':'<->','color':BLUE,'lw':.9,'shrinkA':2,'shrinkB':0},zorder=4)
    ax.text(.3,27.8,r'$\rho(P)=24.6927\,\mathrm{m}$',ha='center',va='bottom',fontsize=10)
    ax.plot(*v.T,'o',color=INK,ms=4,zorder=5)
    for k,(p,offset) in enumerate(zip(v,[(-12,-9),(12,-9),(12,7),(-13,7)]),1):
        ax.annotate(rf'$v_{k}$',p,xytext=offset,textcoords='offset points',fontsize=12,ha='center',va='center')
    ax.plot(*c,'o',ms=3.6,color=INK,zorder=6)
    ax.annotate(r'$c(P)$',c,xytext=(10,-10),textcoords='offset points',fontsize=11,ha='left',va='center')
    handles=[Patch(facecolor='#DCEAF2',edgecolor=BLUE),Line2D([],[],color=BLUE,lw=1.6),Line2D([],[],color=GRAY,lw=.9,ls=':'),Line2D([],[],color=GOLD,lw=1.4,ls='--')]
    fig.legend(handles,['定位区域','最小包围圆','角域边界','最远顶点对'],loc='lower center',bbox_to_anchor=(.52,.002),ncol=2,frameon=False,fontsize=9.5,columnspacing=1.3,handlelength=2)
    fig.savefig(OUT/'q1-numerical-example.pdf')
    fig.savefig(OUT/'q1-numerical-example.png',dpi=400)
    plt.close(fig)
manifest={'figure':'第一问数值计算示例的定位区域与最小包围圆','source':str(SOURCE.relative_to(REPO)),
          'source_data_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'vertices_m':v.tolist(),'diameter_pair_one_based':[i+1,j+1],'center_m':c.tolist(),'radius_m':r,'diameter_m':diameter,
          'max_halfplane_residual_m':float(residual),'width_mm':110,'height_mm':85,'dpi':400,'font':str(font),
          'numpy':np.__version__,'matplotlib':matplotlib.__version__,'coordinates':'source coordinates in original frame, local view [-32,32] m',
          'detectors_outside_view':True,'equal_axis_scale':True,'observations':{'s1_m':[-1000,0],'s2_m':[0,-1000],'bearings_deg':[0,90],'error_bound_deg':1}}
(OUT/'q1-numerical-example-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Saved q1-numerical-example.pdf/png; all numerical geometry checks passed.')
