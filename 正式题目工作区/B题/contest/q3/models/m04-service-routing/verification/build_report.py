"""Generate the v5 research report from immutable per-scene results."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def ci(values):
    a=np.asarray(values,float);m=float(a.mean())
    h=float(t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
    return [m-h,m+h]


def main():
    out=ROOT/'verification/report-v1';out.mkdir(exist_ok=False)
    run=ROOT/'runs/R018-frozen-audit';manifest=json.loads((run/'manifest.json').read_text())
    rows=json.loads((run/'results.json').read_text());assert len(rows)==300
    assert all(r['full'] and r['failures']==0 for r in rows)
    groups={name:sorted([r for r in rows if r['variant']==name],key=lambda r:r['seed']) for name in ['v3','v4','v5']}
    assert all([r['seed'] for r in g]==list(range(12000,12100)) for g in groups.values())
    times={name:np.array([r['per_source_s'] for r in group]) for name,group in groups.items()}
    summary={name:dict(cases=100,mean_s=float(x.mean()),mean_95_t_ci=ci(x),median_s=float(np.median(x)),p90_s=float(np.quantile(x,.9)),
        at_most_200=int((x<=200).sum()),mean_route_m=float(np.mean([r['distance_m'] for r in groups[name]])),
        mean_measures=float(np.mean([r['measures'] for r in groups[name]])),
        mean_tail_s=float(np.mean([r['ledger']['tail_after_last_clear_s'] for r in groups[name]])),
        max_compute_s=max(r['compute_s'] for r in groups[name])) for name,x in times.items()}
    paired=[];comparison={}
    for old in ['v3','v4']:
        difference=times[old]-times['v5']
        comparison[old]=dict(mean_saved_s=float(difference.mean()),saved_95_t_ci=ci(difference),
            reduction_percent=float(100*difference.mean()/times[old].mean()),improved=int((difference>1e-6).sum()),
            worsened=int((difference<-1e-6).sum()),tied=int((abs(difference)<=1e-6).sum()),
            worst_regression_seed=12000+int(np.argmin(difference)),worst_regression_s=float(-difference.min()))
    by_n={str(n):dict(cases=len(indices),**{name:float(times[name][indices].mean()) for name in times})
        for n in range(10,17) if (indices:=[i for i,r in enumerate(groups['v5']) if r['n']==n])}
    for i,r in enumerate(groups['v5']):paired.append(dict(seed=r['seed'],n=r['n'],**{name:float(x[i]) for name,x in times.items()},saving_vs_v3=float(times['v3'][i]-times['v5'][i]),saving_vs_v4=float(times['v4'][i]-times['v5'][i])))
    checker=json.loads((ROOT/'runs/R019-frozen-random-checker/manifest.json').read_text())['summary']
    assert all(g['full']==g['cases'] for g in checker.values())
    result=dict(audit=summary,comparisons=comparison,by_source_count=by_n,checker=checker,target_200_achieved=summary['v5']['mean_s']<=200,
        scope='Synthetic local P3 scenarios only, final parameters frozen before seeds 12000..12099; no official simulator run')
    for name,data in [('summary.json',result),('paired-data.json',paired)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    trial_rows=[];records=0;failed=0
    for folder in sorted((ROOT/'runs').iterdir()):
        file=folder/'manifest.json'
        if not file.exists():trial_rows.append(f'| {folder.name} | — | — | 未完成，不计有效结果 |');continue
        m=json.loads(file.read_text())
        for name,g in m['summary'].items():
            records+=g['cases'];failed+=g['cases']-g['full']
            value=f"{g['mean_s']:.4f}" if g['mean_s'] is not None else '无效：含失败'
            trial_rows.append(f"| {folder.name} | {name} | {g['full']}/{g['cases']} | {value} |")
    (out/'trials.md').write_text('# 本轮全部试验\n\n各批次只作同场比较，不按全表最低值排名。R002失败组的短耗时不算成绩。理想信息诊断不列入候选。\n\n| 批次 | 变体 | 全清/计划场数 | 均值秒/点 |\n|---|---|---:|---:|\n'+'\n'.join(trial_rows)+'\n',encoding='utf-8')
    table='\n'.join(f"| {name} | {g['mean_s']:.4f} | {g['mean_route_m']:.2f} | {g['mean_measures']:.2f} |" for name,g in summary.items())
    counttable='\n'.join(f"| {n} | {g['cases']} | {g['v3']:.2f} | {g['v4']:.2f} | {g['v5']:.2f} |" for n,g in by_n.items())
    v5=summary['v5'];d3=comparison['v3'];d4=comparison['v4']
    report=f'''# 第三问本轮优化与v5独立审计

本轮新增M04模型族，比较服务路径、覆盖布局旋转、沿途补测、初始主动设计、多半径覆盖、未知频道沿途探测、形心/WLS规划位置、暖启动、v4策略融合、连续覆盖证书、后验策略前瞻、联合覆盖路径MILP。全部试验合计{records}次策略执行；其中R002有{failed}次显式规划失败，失败组未计有效成绩，完整记录见trials.md。

当前研究候选是v5服务路径+六朝向覆盖+沿途补测。其余方案未因“数学更复杂”自动采用。**200秒/点目标{'已在本批主审计均值上达到' if result['target_200_achieved'] else '仍未达到'}**；本轮无官方演练成绩，也未登记团队采用。

## 最终同场比较

参数冻结后，12000–12099共100个新场景，v3/v4/v5均100/100完整清除，0次失败清除。主指标为每场全部结束时间T除以实际源数N，再对场景等权平均；全部计入最后清除后的排除时间。

| 策略 | 秒/点 | 每场平均路程m | 每场平均测量次数 |
|---|---:|---:|---:|
{table}

相对v3平均节省{d3['mean_saved_s']:.4f}秒/点（{d3['reduction_percent']:.2f}%），配对节省近似95% t区间[{d3['saved_95_t_ci'][0]:.4f}, {d3['saved_95_t_ci'][1]:.4f}]。相对v4节省{d4['mean_saved_s']:.4f}秒/点（{d4['reduction_percent']:.2f}%），对应区间[{d4['saved_95_t_ci'][0]:.4f}, {d4['saved_95_t_ci'][1]:.4f}]。区间以场景为重复单位，是指定合成分布上的近似采样推断，不是任意布局或官方总体的保证。

相对v4的区间{'全大于0，为该合成分布上的改善提供了统计支持' if d4['saved_95_t_ci'][0]>0 else '未全大于0，不能据此断言v5稳定优于v4；保留两版对照，不作默认替换已有v4目录'}。

v5均值的近似95%区间为[{v5['mean_95_t_ci'][0]:.2f}, {v5['mean_95_t_ci'][1]:.2f}]秒/点，中位数{v5['median_s']:.2f}、90%分位数{v5['p90_s']:.2f}。{v5['at_most_200']}/100场不超过200秒/点，不能用这些场景替代总体均值。相对v4，{d4['improved']}场改善、{d4['worsened']}场退化、{d4['tied']}场持平；最差退化为种子{d4['worst_regression_seed']}，增加{d4['worst_regression_s']:.2f}秒/点。

历史v3均值237.19和历史v4均值242.58来自别的种子，不与本次新均值直接相减计算收益。本报告所有改善均取相同场景配对。

## 什么改动保留下来

覆盖布局在60°周期内试6个朝向，再做删除与连续优化；不会执行尚未覆盖全场的初始布局。路径把测量进入点与预测清除离开点分开，用有向任务代价排路。沿途补测只对预计区域半径能明显收缩的已知频道执行，每次支付真实费用，减少定位不准引起的后续绕行。

选择验证11000–11039中，v3 243.0479、v4 240.9533、fusion 237.7779、全部新功能融合237.9628、形心融合238.2597秒/点。移除服务代价后238.3081，移除沿途补测后241.4997；说明这批样本里沿途补测的贡献更明显，但不是对任意样本的因果保证。连续停止证书与fusion逐场相同，故未加入默认运行路径。

提前远距离探测、按隐含目标数加分的未知频道探测、更多前瞻样本、暖启动、v4全部模块融合都没有在本轮形成足够稳定的优势。联合MILP在8场开发样本相对其v3对照有改善，但未超过主要融合候选的同种子表现；没有因小样本或求解器名称替换最终候选。

## 数学与可复核成果

新连续覆盖函数通过Voronoi极值候选求整个场地上距最近无信号点的最远距离，可单独提供覆盖证据点。160组随机场景与独立Qhull顶点、边界采样的Lipschitz上下界一致，另有4个解析特例。覆盖站选择与开放路径的MILP模型通过20个6节点穷举实例核验。两个模块均保留独立推导和源码；效率不足不否定数学核验，数学核验也不代表整体策略最优。

额外做了起初免费给出真实源坐标的信息诊断，单独放在verification/information-diagnostic-v1。它不是可运行比赛策略，也不是理论下界，不参与本表、候选选择和200秒目标判定。它用于区分路径结构与信息获取造成的开销。

## 稳健性与源数分层

36场边界/近源/近共线/环形压力场景、R固定1000m、误差分别+1°、−1°和棋盘±1°，fusion均全清。前两组比v3略慢，棋盘组略快，未隐去退化。

冻结后另测14000–14029的30个均匀随机布局，误差改为固定位置棋盘±1°。v3 {checker['v3']['mean_s']:.4f}、v5 {checker['v5']['mean_s']:.4f}秒/点，均30/30全清。这是单独的误差敏感性结果，不混入主审计均值。

| 源数 | 场数 | v3秒/点 | v4秒/点 | v5秒/点 |
|---:|---:|---:|---:|---:|
{counttable}

少源场景必须把排除未知频道的整场覆盖费用摊到较少的源上。不能假定已发现数量就是实际数量，或省略最后排除来达到更低指标。各源数子组样本较小，仅作描述。

## 运行与证据保存

当前v5单场最大本地计算耗时{v5['max_compute_s']:.2f}秒；虚拟移动/测量费用和计算墙钟分开记录。最终审计保存参数、源码快照及散列、所有场景、每场每策略完整动作和完成证书，未只保存均值。新运行包与旧v3/v4并存，用户执行官方演练；本轮没有调用官方接口。

主报告、图和表全部由verification/build_report.py从R018/R019原始JSON生成。数学表述见formulations/v01.md，参数冻结决定见verification/selection-v05.md。当前新增研究保存本地，未提交推送；此前GitHub草稿PR #7仍是此前成果的审阅入口。

剩余缺口是整体发现、定位与未来路径的联合决策，当前局部预测还不能准确估计新源发现后的绕行。{'这批结果不等于任意合法场景都达到200秒。' if result['target_200_achieved'] else '本轮完成了进一步策略研究与验证，但没有解决200秒目标；不能宣称目标不可能，也不能把研究候选当成达标交付。'}
'''
    (out/'本轮优化与结果.md').write_text(report,encoding='utf-8')
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42}):
        fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
        move=np.array([np.mean([r['distance_m']/5/r['n'] for r in groups[n]]) for n in groups])
        sensing=np.array([np.mean([(5*r['measures']+r['switches'])/r['n'] for r in groups[n]]) for n in groups])
        axes[0].bar(list(groups),move,color='#0072B2',label='Moving')
        axes[0].bar(list(groups),sensing,bottom=move,color='#E69F00',hatch='//',label='Measuring / switching')
        axes[0].bar(list(groups),np.full(3,5),bottom=move+sensing,color='#666666',label='Clearing')
        axes[0].axhline(200,linestyle='--',color='black',linewidth=1,label='200 s/source target')
        axes[0].set(ylabel='Mean time (s/source)',title='A  Complete action costs (n=100)',ylim=(0,max(x.mean() for x in times.values())*1.32));axes[0].legend(frameon=False,fontsize=8,loc='upper left')
        saved=times['v4']-times['v5'];axes[1].scatter(np.arange(1,101),saved,color='#0072B2',s=18)
        axes[1].axhline(0,color='#666666',linestyle='--');axes[1].axhline(saved.mean(),color='#D55E00',label=f'Mean saving {saved.mean():.2f} s/source')
        axes[1].set(xlabel='Scene index (seeds 12000–12099)',ylabel='v4 minus v5 (s/source)',title='B  Savings and regressions');axes[1].legend(frameon=False,fontsize=8)
        fig.savefig(out/'audit-v5.png',dpi=220);fig.savefig(out/'audit-v5.pdf');plt.close(fig)
    provenance=dict(source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'results.json',run/'manifest.json',ROOT/'runs/R019-frozen-random-checker/manifest.json',Path(__file__)]},
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,figure_inches=[10,4.2],png_dpi=220,
        replicate='scene',estimator='equal-weight mean of each complete T/N',uncertainty='two-sided approximate Student t 95% interval across scenes',exclusions='none in final audit',
        figure_alt='Left: all moving, measuring/switching and clearing costs, with a 200-second target line. Right: every paired v4-v5 time saving, including regressions.',destination='research and later contest-paper draft; no publisher-specific compliance claimed')
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
