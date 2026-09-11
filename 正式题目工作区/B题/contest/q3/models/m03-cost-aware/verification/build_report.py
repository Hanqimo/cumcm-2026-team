"""Generate tables, paired statistics and figures directly from frozen results."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def interval(values):
    a=np.asarray(values,float);mean=float(a.mean())
    half=float(t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
    return [mean-half,mean+half]


def main():
    out=ROOT/'verification/report-v1';out.mkdir(exist_ok=False)
    run=ROOT/'runs/R009-frozen-audit'
    manifest=json.loads((run/'manifest.json').read_text())
    rows=json.loads((run/'results.json').read_text())
    assert len(rows)==200 and all(r['full'] and r['failures']==0 for r in rows)
    pair={}
    for r in rows:pair.setdefault(r['seed'],{})[r['variant']]=r
    assert sorted(pair)==list(range(9000,9100))
    paired=[dict(seed=s,n=p['baseline']['n'],baseline=p['baseline']['per_source_s'],combined=p['combined']['per_source_s'],
                 saved=p['baseline']['per_source_s']-p['combined']['per_source_s']) for s,p in sorted(pair.items())]
    d=np.array([p['saved'] for p in paired]);a=np.array([p['baseline'] for p in paired]);b=np.array([p['combined'] for p in paired])
    result=dict(cases=len(paired),baseline_mean=float(a.mean()),combined_mean=float(b.mean()),mean_saved=float(d.mean()),
        relative_mean_reduction_percent=float(100*(a.mean()-b.mean())/a.mean()),paired_saved_95_t_ci=interval(d),
        combined_mean_95_t_ci=interval(b),median=float(np.median(b)),p90=float(np.quantile(b,.9)),
        improved=int((d>1e-6).sum()),worsened=int((d<-1e-6).sum()),tied=int((abs(d)<=1e-6).sum()),
        at_most_200=int((b<=200).sum()),at_most_220=int((b<=220).sum()),all_full=True,failed_clears=0,
        worst_regression=max(paired,key=lambda r:-r['saved']),largest_saving=max(paired,key=lambda r:r['saved']),
        by_n={str(n):dict(cases=len(g),baseline=float(np.mean([p['baseline'] for p in g])),combined=float(np.mean([p['combined'] for p in g])))
              for n in range(10,17) if (g:=[p for p in paired if p['n']==n])},
        audit_summary=manifest['summary'],interval_scope='Approximate t interval across generated scenes, not official distribution or adversarial guarantee')
    for name,data in [('summary.json',result),('paired-data.json',paired)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    trials=[]
    for folder in sorted((ROOT/'runs').iterdir()):
        if not (folder/'manifest.json').exists():
            trials.append(f'| {folder.name} | 未完成清单 | 不计有效结果 |');continue
        m=json.loads((folder/'manifest.json').read_text())
        text='；'.join(f"{name} {v['mean_s']:.4f}（{v['full']}/{v['cases']}全清）" if v['mean_s'] is not None else f'{name}失败' for name,v in m['summary'].items())
        trials.append(f'| {folder.name} | {text} | {m["layout"]} / {m["error_model"]} |')
    (out/'trials.md').write_text('# 全部本轮试验\n\n单位：秒/点。不同批次不直接比较均值；各行均有自己的同场baseline。\n\n| 运行 | 候选均值与完整性 | 布局/误差 |\n|---|---|---|\n'+'\n'.join(trials)+'\n',encoding='utf-8')
    source_rows=[]
    for n,g in result['by_n'].items():source_rows.append(f"| {n} | {g['cases']} | {g['baseline']:.2f} | {g['combined']:.2f} |")
    lo,hi=result['paired_saved_95_t_ci'];meanlo,meanhi=result['combined_mean_95_t_ci']
    report=f'''# 本轮论文启发改进与独立审计

本轮状态：Q1/Q2两项几何补充已独立核验；Q3 M03 v4完成开发、选择验证、参数冻结和100场独立本地审计。属于研究候选，未登记团队采用，未运行官方演练。200秒/点目标尚未达成。

## 相同场景的核心比较

最终审计固定9000–9099，100场，每场全向源10–16个，面积均匀生成、R均匀生成在[1000,1500]，误差为固定位置的有界sin函数加两位小数舍入。全部200次策略执行完整清除，无失败清除。指标为每场包含最后收尾的总时间T除以实际源数N，再对场景等权平均。

| 策略 | 秒/点 | 每场平均路程m | 每场平均测量次数 |
|---|---:|---:|---:|
| 原v3组合策略 | {a.mean():.4f} | {manifest['summary']['baseline']['mean_distance_m']:.2f} | {manifest['summary']['baseline']['mean_measures']:.2f} |
| 新v4组合策略 | {b.mean():.4f} | {manifest['summary']['combined']['mean_distance_m']:.2f} | {manifest['summary']['combined']['mean_measures']:.2f} |

平均节省{d.mean():.4f}秒/点，即{result['relative_mean_reduction_percent']:.2f}%。配对节省的近似95% t区间为[{lo:.4f}, {hi:.4f}]秒/点。该区间以场景为重复单位，反映这个合成分布上的采样不确定性，不能解释成官方场景性能保证，也不覆盖任意误差场。

新策略均值的近似95% t区间为[{meanlo:.2f}, {meanhi:.2f}]秒/点，中位数{result['median']:.2f}，90%分位数{result['p90']:.2f}；{result['at_most_200']}/100场不超过200秒/点。相对旧版{result['improved']}场改善、{result['worsened']}场变慢、{result['tied']}场持平。最差退化是种子{result['worst_regression']['seed']}，增加{-result['worst_regression']['saved']:.2f}秒/点；没有隐去退化案例。

此前v3的200场均值237.19来自另一组种子，不能直接拿它与本次v4均值相减报告收益。这里所有节省均来自同场配对。

## 各项改进和证据

第一问：从只在线段上找安全清除位置，改成求全部保证清除位置的最近点。等半径圆盘交可用圆弧投影和两圆交点有限枚举；200例独立凸优化核验最大距离差3.25×10⁻⁷m，同场几何局部平均少走0.7704m。局部清除距离不增不代表整场路径必然变短。

第二问：把当前区域P带入保证接收判定，有限枚举多边形顶点、边圆交点和圆弧极值。300组、120万个直接位置核验通过，并保留一个旧充分条件拒绝、新判据接受的可手算例子。对完整历史仍为充分条件，不冒充完整物理状态的最大接收域。

第三问：将移动、后续测量、接近清除共同计入测点预测成本；将多个目标节点的扫描任务合并到有完整覆盖证书的新站点。开发过程中比较均值、混合和最大场景成本、出口成本、中途共享测量、仅合并独立站和允许目标任务合并。中途共享及仅独立站合并没有稳定收益，保留负结果，详见trials.md。最终采用9个代表场景的最大预测成本，加三轮覆盖站优化；这不是连续minimax最优策略。

选择验证集8000–8039中，v3为248.44、仅成本246.32、仅任务合并246.86、组合243.95秒/点，均40/40全清。24场边界/近源/近共线/环形压力场景，R固定1000、误差分别+1°、−1°、棋盘±1°，四个策略均全清；压力场景不是随机总体样本，不与均匀样本混合估计均值。组合在棋盘误差压力组略慢，未把全清等同于总是提速。

## 源数分层

| 源数 | 场数 | v3秒/点 | v4秒/点 |
|---:|---:|---:|---:|
{chr(10).join(source_rows)}

这组分层仅描述样本：源数少时用于排除未知频道的覆盖成本摊到每个源上更高。不能据此跳过尾部排除、假定实际数量或以已发现数量提前结束。

## 可复现性与下一步

源码、参数、全部场景、散列和逐场结果保存在runs/R009-frozen-audit。冻结决定见verification/selection-v04.md；数学推导见formulations和前两问v02；本轮原论文具体页码、迁移范围与散列见literature。数据表和图由build_report.py生成，没有手改结果。

新组合策略单场最大本地计算耗时{manifest['summary']['combined']['max_compute_s']:.2f}秒；旧版为{manifest['summary']['baseline']['max_compute_s']:.2f}秒。增加的计算用于有限场景预测，虚拟动作成本与计算墙钟分开记录。运行包保留v3以及两个消融候选，官方演练留给用户执行。

下一步更值得验证“区域的进入测量点—清除出口”的联合路径决策，及实际演练的搜索尾部成本；不要继续只调几个横向偏移或宣称局部几何精化能消除剩余全部差距。Song等的服务线段路线提供方向，但本轮未实现。仍缺任意合法布局的完成性证明、任意有界空间误差的性能保证和官方实测成绩。
'''
    (out/'本轮改进与结果.md').write_text(report,encoding='utf-8')
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42}):
        fig,axes=plt.subplots(1,2,figsize=(10,4.1),layout='constrained')
        limits=[min(a.min(),b.min())-8,max(a.max(),b.max())+8]
        axes[0].scatter(a,b,s=22,marker='o',facecolors='none',edgecolors='#0072B2',linewidths=.8)
        axes[0].plot(limits,limits,'--',color='#555555',linewidth=1,label='Equal time')
        axes[0].set(xlim=limits,ylim=limits,xlabel='v3 time (s/source)',ylabel='v4 time (s/source)',title='A  Paired scenes (n=100)')
        axes[0].set_aspect('equal',adjustable='box');axes[0].legend(frameon=False)
        axes[1].axhline(0,color='#555555',linestyle='--',linewidth=1)
        axes[1].scatter(np.arange(1,len(d)+1),d,s=18,color='#0072B2',marker='o')
        axes[1].axhline(d.mean(),color='#D55E00',linestyle='-',linewidth=1.3,label=f'Mean saving {d.mean():.2f} s/source')
        axes[1].set(xlabel='Scene index (seeds 9000–9099)',ylabel='v3 minus v4 (s/source)',title='B  Savings and regressions')
        axes[1].legend(frameon=False,loc='best')
        fig.savefig(out/'paired-audit.png',dpi=220);fig.savefig(out/'paired-audit.pdf');plt.close(fig)
    provenance=dict(source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'results.json',run/'manifest.json',Path(__file__)]},
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,
        figure_dimensions_in=[10,4.1],png_dpi=220,replicate='one generated scene',exclusions='none',
        transformation='T/N per scene; paired difference v3-v4; no smoothing or clipping',
        uncertainty='two-sided 95% Student t interval on scene means/differences',
        figure_alt='Left: every audited scene as old versus new time, with equality line. Right: every paired saving in seed order, retaining negative regressions.',
        destination='research and later contest-paper draft; no journal-specific compliance claimed')
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
