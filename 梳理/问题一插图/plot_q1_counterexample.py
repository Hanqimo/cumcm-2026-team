"""等边三角形反例：边长 38 m，直径圆半径 19 m。独立输出，不覆盖历史组合图。

Run: python3 梳理/问题一插图/plot_q1_counterexample.py
Dependencies: numpy, matplotlib; optionally set CJK_FONT to a Chinese font file.
"""
from pathlib import Path
import hashlib,json,os
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.patches import Polygon,Circle,Arc
from matplotlib.lines import Line2D

OUT=Path(__file__).resolve().parent
candidates=[os.environ.get('CJK_FONT',''),'/Applications/Microsoft Word.app/Contents/Resources/DFonts/SimHei.ttf',
            '/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
font=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
if font is None:raise RuntimeError('请通过 CJK_FONT 指定中文字体文件。')
font_manager.fontManager.addfont(str(font));family=font_manager.FontProperties(fname=str(font)).get_name()
BLUE,GOLD,INK='#356C91','#A97A26','#253746'
L=38.;vertices=np.array([[0.,0.],[L,0.],[L/2,L*np.sqrt(3)/2]])
midpoint=(vertices[0]+vertices[1])/2;radius=L/2
third_distance=float(np.linalg.norm(vertices[2]-midpoint));true_radius=L/np.sqrt(3)
assert third_distance>radius and true_radius>20
style={'font.family':family,'font.size':10.5,'mathtext.fontset':'stix','axes.unicode_minus':False,
       'pdf.fonttype':42,'ps.fonttype':42,'text.color':INK,'figure.facecolor':'white','savefig.facecolor':'white'}
with plt.rc_context(style):
    fig,ax=plt.subplots(figsize=(110/25.4,70/25.4))
    fig.subplots_adjust(left=.015,right=.995,bottom=.14,top=.99)
    ax.set_aspect('equal');ax.set(xlim=(-5,66),ylim=(-22,40));ax.axis('off')
    ax.add_patch(Circle(midpoint,radius,facecolor='#F9F5EA',edgecolor='none',zorder=1))
    ax.add_patch(Polygon(vertices,closed=True,facecolor='#C6DDEB',alpha=.72,edgecolor=BLUE,lw=1.6,zorder=2))
    ax.add_patch(Circle(midpoint,radius,fill=False,edgecolor=GOLD,ls=(0,(5,3)),lw=1.6,zorder=3))
    ax.plot(*vertices.T,'o',color=INK,ms=4.1,zorder=4)
    ax.plot(*midpoint,'o',color=INK,ms=3.5,zorder=4)
    for label,p,offset in [(r'$v_1$',vertices[0],(-10,-4)),(r'$v_2$',vertices[1],(14,-4)),(r'$v_3$',vertices[2],(-5,6)),(r'$M$',midpoint,(0,-12))]:
        ax.annotate(label,p,xytext=offset,textcoords='offset points',fontsize=12,ha='center',zorder=6)
    ax.add_patch(Arc(vertices[2],11,11,theta1=240,theta2=300,color=INK,lw=1,zorder=3))
    ax.text(19,24,r'$60^\circ$',ha='center',va='center',fontsize=11)
    ax.text(19,12,r'$T$',ha='center',va='center',fontsize=14,color=BLUE)
    ax.annotate('第三个顶点在圆外',xy=vertices[2],xytext=(43,33),ha='left',va='center',fontsize=10,
                arrowprops={'arrowstyle':'->','lw':1,'color':INK,'shrinkB':5})
    ax.text(45,24,r'$\angle v_1v_3v_2=60^\circ<90^\circ$',ha='left',va='center',fontsize=10)
    ax.annotate('',xy=vertices[1]+[0,-8],xytext=vertices[0]+[0,-8],arrowprops={'arrowstyle':'<->','color':INK,'lw':.8})
    ax.text(19,-12.5,r'$\operatorname{diam}(T)=38\,\mathrm{m}$',ha='center',va='center',fontsize=10)
    handles=[Line2D([],[],color=BLUE,lw=1.6),Line2D([],[],color=GOLD,lw=1.6,ls='--')]
    fig.legend(handles,['定位区域',r'直径圆（半径 $19\,\mathrm{m}$）'],loc='lower center',bbox_to_anchor=(.5,.015),ncol=2,frameon=False,fontsize=10,handlelength=1.8,columnspacing=1.2)
    fig.savefig(OUT/'q1-counterexample.pdf')
    fig.savefig(OUT/'q1-counterexample.png',dpi=400)
    plt.close(fig)
manifest={'figure':'等边三角形的直径圆不能覆盖整个区域','construction':'analytic equilateral triangle',
          'vertices_m':vertices.tolist(),'circle_center_m':midpoint.tolist(),'circle_radius_m':radius,
          'third_vertex_distance_to_center_m':third_distance,'true_minimum_enclosing_radius_m':true_radius,
          'third_vertex_angle_degrees':60,'width_mm':110,'height_mm':70,'png_dpi':400,'font':str(font),
          'matplotlib':matplotlib.__version__,'numpy':np.__version__,'equal_scale':True,
          'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'q1-counterexample-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
