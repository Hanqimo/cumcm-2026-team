"""Paper Q1 figures: schematic geometry and unchanged R003 numerical examples.

Run with Python + numpy/matplotlib/Pillow. Outputs PDF and 400-dpi PNG here.
Figure 1 angles are enlarged for illustration; Figure 2 uses actual +/-1 deg data.
"""
from pathlib import Path
import hashlib
import json
import os
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/q1-paperfig-mpl')
try:
    import matplotlib
except ImportError:
    sys.path.insert(0, '/private/tmp/bq2-plot-deps')
    import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, Circle, Arc
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DATA = REPO / 'contest/q1/models/m01-bounded-bearing/runs/R003'
FONT = Path('/Applications/Microsoft Word.app/Contents/Resources/DFonts/SimHei.ttf')
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
INK, BLUE, GOLD = '#253746', '#356C91', '#A97A26'
WEDGE, WEDGE_EDGE, OVERLAP = '#F2EBD3', '#B7A977', '#C6DDEB'
STYLE = {
    'font.family': 'SimHei', 'font.size': 10.5, 'mathtext.fontset': 'stix',
    'axes.unicode_minus': False, 'axes.labelsize': 10, 'axes.titlesize': 10.5,
    'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 10,
    'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': '#8A9298',
    'xtick.color': INK, 'ytick.color': INK, 'axes.linewidth': .65,
    'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'path',
    'savefig.facecolor': 'white', 'figure.facecolor': 'white',
}


def unit(deg):
    return np.array([np.cos(np.deg2rad(deg)), np.sin(np.deg2rad(deg))])


def constraints(s, theta, alpha):
    lo, hi = unit(theta-alpha), unit(theta+alpha)
    a = np.array([[lo[1], -lo[0]], [-hi[1], hi[0]]])
    return a, a @ np.asarray(s)


def clip(poly, a, b):
    for n, rhs in zip(a, b):
        result = []
        for p, q in zip(poly, np.roll(poly, -1, axis=0)):
            fp, fq = n @ p - rhs, n @ q - rhs
            if fp <= 1e-10:
                result.append(p)
            if (fp <= 0) != (fq <= 0):
                result.append(p + fp / (fp-fq) * (q-p))
        poly = np.array(result)
    return poly


def sensor(ax, s, index, offset=(-1, -14)):
    ax.plot(*s, 'o', ms=4.8, color=INK, zorder=8)
    ax.annotate(rf'$s_{index}$', s, xytext=offset,
                textcoords='offset points', fontsize=13, ha='center', zorder=9)


def wedge(ax, s, theta, alpha, length):
    s = np.asarray(s)
    ends = [s + length * unit(theta-alpha), s + length * unit(theta+alpha)]
    ax.add_patch(Polygon([s, *ends], facecolor=WEDGE, edgecolor='none', zorder=1))
    for end in ends:
        ax.plot(*np.array([s, end]).T, color=WEDGE_EDGE, lw=.95, zorder=2)


def export(fig, name):
    fig.savefig(OUT / (name+'.pdf'))
    fig.savefig(OUT / (name+'.png'), dpi=400)
    plt.close(fig)


def schematic():
    fig, axes = plt.subplots(1, 3, figsize=(160/25.4, 59/25.4))
    fig.subplots_adjust(left=.01, right=.99, bottom=.19, top=.83, wspace=.12)
    for ax in axes:
        ax.set_aspect('equal')
        ax.set_axis_off()
    ax = axes[0]
    ax.set(xlim=(-.45, 5), ylim=(-.7, 4.1))
    wedge(ax, (0, 0), 35, 12, 5.3)
    ax.annotate('', xy=4.8*unit(35), xytext=(0, 0),
                arrowprops=dict(arrowstyle='->', color=INK, lw=1.2))
    ax.add_patch(Arc((0, 0), 3.5, 3.5, theta1=23, theta2=35,
                     color=INK, lw=.7))
    ax.text(1.55, .57, r'$\alpha$', fontsize=13)
    ax.text(2.15, 1.65, r'$\theta_1$', fontsize=13)
    ax.text(3.45, 3.15, r'$W_1$', fontsize=14)
    sensor(ax, (0, 0), 1)

    ax = axes[1]
    ax.set(xlim=(-.55, 6.55), ylim=(-.65, 4.5))
    specs = [((0, 0), 30, 12), ((6, 0), 150, 12)]
    polygon = np.array([[-10, -10], [15, -10], [15, 15], [-10, 15]])
    for s, theta, alpha in specs:
        wedge(ax, s, theta, alpha, 6.3)
        polygon = clip(polygon, *constraints(s, theta, alpha))
    assert len(polygon) == 4
    ax.add_patch(Polygon(polygon, facecolor=OVERLAP, edgecolor=BLUE, lw=1.2, zorder=3))
    g = polygon.mean(axis=0)
    ax.plot(*g, 'o', color=INK, ms=3.8, zorder=5)
    ax.annotate(r'$g$', g, xytext=(5, 5), textcoords='offset points', fontsize=13)
    sensor(ax, (0, 0), 1)
    sensor(ax, (6, 0), 2)

    ax = axes[2]
    ax.set(xlim=(-.5, 6.3), ylim=(-.8, 4.5))
    specs = [((0, 0), 35, 12), ((2, -.2), 35, 12)]
    viewport = np.array([[-.5, -.8], [6.3, -.8], [6.3, 4.5], [-.5, 4.5]])
    polygon = viewport.copy()
    for i, (s, theta, alpha) in enumerate(specs, 1):
        a, b = constraints(s, theta, alpha)
        region = clip(viewport.copy(), a, b)
        ax.add_patch(Polygon(region, facecolor=WEDGE, edgecolor='none', zorder=1))
        polygon = clip(polygon, a, b)
        for angle in (theta-alpha, theta+alpha):
            ax.plot(*np.array([s, np.asarray(s)+10*unit(angle)]).T,
                    color=WEDGE_EDGE, lw=.85, ls=':', zorder=2)
        sensor(ax, s, i)
    ax.add_patch(Polygon(polygon, facecolor=OVERLAP, edgecolor='none', zorder=3))
    # The active lower/upper rays meet here. No artificial closing edge is drawn.
    a1, b1 = constraints((0, 0), 35, 12)
    a2, b2 = constraints((2, -.2), 35, 12)
    vertex = np.linalg.solve(np.array([a1[0], a2[1]]), [b1[0], b2[1]])
    for angle in (23, 47):
        end = vertex + 5.0*unit(angle)
        ax.plot(*np.array([vertex, end]).T, color=BLUE, lw=1.2, zorder=4)
        tip = vertex + (2.5 if angle == 23 else 3.0)*unit(angle)
        ax.annotate('', tip, tip-.6*unit(angle),
                    arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.2), zorder=5)
    ax.text(4.3, 2.0, r'$P$', fontsize=14, color=BLUE, zorder=6)
    for ax, title, footer in zip(axes,
            ['(a) 单次观测', '(b) 有界交集', '(c) 无界交集'],
            ['前向角域', r'$P=W_1\cap W_2$', '沿箭头方向无限延伸']):
        pos = ax.get_position()
        center = (pos.x0+pos.x1)/2
        fig.text(center, .94, title, ha='center', va='top')
        fig.text(center, .04, footer, ha='center', va='bottom',
                 color=INK if ax is axes[0] else BLUE)
    export(fig, 'q1-intersection-process')


def coverage():
    tri = json.loads((DATA/'counterexample.json').read_text())
    orth = json.loads((DATA/'orthogonal_example.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(135/25.4, 78/25.4))
    fig.subplots_adjust(left=.10, right=.99, bottom=.25, top=.89, wspace=.38)
    for ax, result, title in zip(axes, (tri, orth), ('(a) 等边三角形', '(b) 正交测向交会')):
        vertices = np.array(result['vertices'])
        c, r = np.array(result['cover_center']), result['cover_radius_m']
        ax.add_patch(Polygon(vertices, facecolor=OVERLAP, edgecolor=BLUE, lw=.9))
        ax.add_patch(Circle(c, r, fill=False, edgecolor=BLUE, lw=1.35))
        pair = vertices[result['diameter_pair']]
        mid, halfdiam = pair.mean(axis=0), result['diameter_m']/2
        ax.add_patch(Circle(mid, halfdiam, fill=False, edgecolor=GOLD, lw=1.1, ls='--'))
        ax.scatter(*vertices.T, color=INK, s=10, zorder=4)
        ax.set(xlabel=r'$x\,/\,\mathrm{m}$', ylabel=r'$y\,/\,\mathrm{m}$', title=title)
        ax.set_aspect('equal')
        ax.tick_params(length=2.5, pad=3)
        ax.grid(color='#E4E8EB', lw=.55)
        ax.set_axisbelow(True)
        assert np.max(np.linalg.norm(vertices-c, axis=1)) <= r+1e-7
    axes[0].set(xlim=(-6, 44), ylim=(-22, 36), xticks=[0, 20, 40], yticks=[-20, 0, 20])
    axes[1].set(xlim=(-29, 29), ylim=(-29, 29), xticks=[-20, 0, 20], yticks=[-20, 0, 20])
    assert abs(tri['cover_radius_m']-38/np.sqrt(3)) < 1e-7
    assert abs(orth['cover_radius_m']-orth['diameter_m']/2) < 1e-7
    fig.legend([Line2D([], [], color=BLUE, lw=1.35), Line2D([], [], color=GOLD, lw=1.1, ls='--')],
               ['最小包围圆', '直径圆'], loc='lower center', bbox_to_anchor=(.55, .035),
               frameon=False, ncol=2, handlelength=2.0, columnspacing=1.5)
    export(fig, 'q1-geometry')


if __name__ == '__main__':
    with plt.rc_context(STYLE):
        schematic()
        coverage()
    manifest = {
        'source_data': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [DATA/'counterexample.json', DATA/'orthogonal_example.json']},
        'figure_1': {'kind': 'schematic', 'width_mm': 160, 'height_mm': 59,
                     'angles_enlarged_for_visibility': True, 'sensor_marker': 'circle'},
        'figure_2': {'kind': 'unchanged_R003_geometry', 'width_mm': 135, 'height_mm': 78,
                     'bearing_error_degrees': 1, 'axis_units': 'm'},
        'font': str(FONT), 'font_pt': {'body': 10.5, 'ticks': 9},
        'numpy': np.__version__, 'matplotlib': matplotlib.__version__, 'png_dpi': 400,
    }
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('Saved two figures as PDF + PNG; numerical geometry checks passed.')
