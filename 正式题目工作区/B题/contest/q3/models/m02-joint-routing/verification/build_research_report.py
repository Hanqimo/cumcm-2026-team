"""Audit all recorded trials and export an honest final comparison."""
import collections
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'verification/research-report-v1'
AUDIT=ROOT/'runs/R039-final-audit-recovery'
LABELS={'baseline':'M01 旧版','route_guard':'联合路径','region_coupled':'区域收缩',
        'continuous_cover':'连续覆盖','combined_cover':'组合策略'}


def stats(rows):
    good=all(r['full_clear'] and not r['error'] for r in rows)
    y=np.array([r['per_source_s'] for r in rows])
    ci=float(t.ppf(.975,len(y)-1)*np.std(y,ddof=1)/np.sqrt(len(y))) if len(y)>1 else None
    return dict(cases=len(rows),full=sum(r['full_clear'] and not r['error'] for r in rows),
        eligible=good,mean=float(y.mean()) if good else None,
        mean_ci95=[float(y.mean()-ci),float(y.mean()+ci)] if ci is not None and good else None,
        median=float(np.median(y)) if good else None,p90=float(np.quantile(y,.9)) if good else None,
        pooled_time_per_source=sum(r['time_s'] for r in rows)/sum(r['n'] for r in rows) if good else None,
        at_most_200=sum(r['per_source_s']<=200 for r in rows) if good else None,
        at_most_220=sum(r['per_source_s']<=220 for r in rows) if good else None,
        mean_distance_m=float(np.mean([r['distance_m'] for r in rows])),
        mean_move_per_source_s=float(np.mean([r['distance_m']/5/r['n'] for r in rows])),
        mean_other_per_source_s=float(np.mean([(r['time_s']-r['distance_m']/5)/r['n'] for r in rows])),
        mean_measures=float(np.mean([r['measures'] for r in rows])),
        clear_failures=sum(r['failures'] for r in rows),max_compute_s=max(r['elapsed_s'] for r in rows))


def main():
    assert (AUDIT/'manifest.json').exists(),'Wait for completed audit'
    OUT.mkdir(exist_ok=False)
    rows=json.loads((AUDIT/'results.json').read_text(encoding='utf-8'))
    assert len(rows)==1000 and len({r['seed'] for r in rows})==200
    summary={k:stats([r for r in rows if r['variant']==k]) for k in LABELS}
    assert all(r['eligible'] for r in summary.values())
    by_n={k:{n:stats([r for r in rows if r['variant']==k and r['n']==n]) for n in range(10,17)} for k in LABELS}
    best=min([k for k in LABELS if k!='baseline'],key=lambda k:summary[k]['mean'])
    trials=[];invalid=[]
    for d in sorted((ROOT/'runs').iterdir()):
        if not d.is_dir():continue
        try:rr=json.loads((d/'results.json').read_text(encoding='utf-8'))
        except Exception as error:
            invalid.append(dict(run=d.name,status='unreadable_or_truncated',error=type(error).__name__));continue
        if not (d/'manifest.json').exists():
            invalid.append(dict(run=d.name,status='incomplete_no_manifest',retained_rows=len(rr)));continue
        for k in sorted({r['variant'] for r in rr}):
            group=[r for r in rr if r['variant']==k]
            trials.append(dict(run=d.name,variant=k,**stats(group)))
    all_summary=dict(final_audit=summary,by_target_count=by_n,best_observed_candidate=best,
        target_200_achieved=False,completed_trial_comparisons=trials,incomplete_runs=invalid,
        metric='Mean over all scenes of total completion time / actual source count. Incomplete runs are ineligible.',
        total_completed_scene_strategy_runs=sum(r['cases'] for r in trials))
    (OUT/'summary.json').write_text(json.dumps(all_summary,indent=2,ensure_ascii=False),encoding='utf-8')
    (OUT/'paired-data.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    lines=['# 第三问优化研究记录：200 秒目标尚未达成','',
        '本轮保留了多条可运行候选及失败尝试。下表来自最后冻结后的 200 个合成场景（种子 5100–5299），所有策略使用相同布点、接收半径和空间固定角度误差。正式模拟器没有在本轮重新运行。','',
        '| 策略 | 全清 | 均值（秒/点） | 中位数 | 90%分位数 | 平均路程（米） | 平均检测次数 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for k,v in summary.items():lines.append(f'| {LABELS[k]} | {v["full"]}/200 | {v["mean"]:.2f} | {v["median"]:.2f} | {v["p90"]:.2f} | {v["mean_distance_m"]:.1f} | {v["mean_measures"]:.2f} |')
    v=summary[best];improvement=100*(1-v['mean']/summary['baseline']['mean'])
    lines+=['',f'本次审计中均值最低的是 **{LABELS[best]}**：{v["mean"]:.2f} 秒/点，比同场景 M01 旧版均值降低 {improvement:.2f}%。条件于本地随机场景生成规则的均值 95% t 区间为 [{v["mean_ci95"][0]:.2f}, {v["mean_ci95"][1]:.2f}] 秒/点；它不是官方成绩或官方场景泛化保证。',
        f'其中 ≤200 秒/点 {v["at_most_200"]}/200，≤220 秒/点 {v["at_most_220"]}/200。不能用这些子集替代全部场景的均值。距离 200 秒的差额仍有 {v["mean"]-200:.2f} 秒/点。',
        '', '## 按实际目标数分层','',
        '| 实际数量 | 场景数 | 旧版均值 | 本次最佳候选均值 |', '|---|---:|---:|---:|']
    for n in range(10,17):lines.append(f'| {n} | {by_n[best][n]["cases"]} | {by_n["baseline"][n]["mean"]:.2f} | {by_n[best][n]["mean"]:.2f} |')
    lines+=['','## 指标与数据边界','',
        '- 每场指标为 T/N：T 包括所有移动、测量、切换频道、清除及收尾搜索；N 为实际源总数，并要求全部清除。主表取场景等权均值，汇总 T/汇总 N 另存 JSON，不混用。',
        '- 合成普通场景：N 在 10–16 随机抽取，位置在半径 1800 m 圆内按面积均匀分布，R 在 1000–1500 m 均匀分布，方向误差为空间固定正弦误差并舍入两位小数。分布是测试约定，不是题目给出的概率规律。',
        '- 开发使用 200–219；300–399 曾参与候选比较；5000–5099 是先前冻结候选的独立比较，后来用于判断研究方向，不能充当组合策略最终留出集。最后一轮为 5100–5299，冻结后没有据其结果再调参。',
        '- R035 最终审计进程中断，results.json 截断，未形成 manifest。R039 按原定种子、配置和相同策略代码重跑，并改用原子写入保护日志；未更换困难案例。',
        '- 200 场用于同时比较四个冻结候选；“最佳”是该表中的最佳观测值，不宣称全局最优。',
        '', '## 主要方向及结果','',
        '1. 联合路径：把已知目标与未覆盖区域扫描点放进同一条开放路径，以 2-opt 改善顺序；起始短基线和有条件补测减少定位往返。',
        '2. 区域收缩：联合使用无信号圆盘排除及固定接收半径蕴含的正/负观测距离次序，缩小 Q1 可行区域。独立贡献较小。',
        '3. 连续覆盖：先删除冗余扫描站，再在仍覆盖所有责任网格角点的条件下移动扫描站，使相邻路径缩短；每次移动后检查完整网格覆盖。',
        '4. 组合策略：把区域收缩和连续覆盖合并。保留其单独消融策略，避免把所有变化混在一起无法解释。',
        '5. 已尝试但未选为默认：固定扇区巡行、先侦察后清除、短探针、试清、逐动作重排、覆盖收益加权、固定扫描计划、沿路插点、基于信念采样的前瞻推演。完整参数与失败记录见 trials.md 和各 runs 目录。',
        '', '## 验证与局限','',
        '- 最终审计每个候选均接受真实位置位于外包多边形的独立叉积检查，以及实际清除距离与声明上界的核对。所有扫描停止判据使用已执行的无信号记录，未来计划的覆盖不能当作完成证据。',
        '- 额外压力集覆盖边界环形、原点附近、极端聚集及 R=1000，误差采用恒定 +1°、恒定 −1° 和空间棋盘 ±1°。具体数量与结果见 runs/R031–R033、R036–R038。压力案例有限，不能证明任意场景都能在迭代上限内完成。',
        '- integration-audit.json 记录运行包工厂与审计参数完全一致、日志 JSON 可序列化，以及负观测几何的额外数值核查。覆盖和区域公式的解释见 formulations/v01.md。',
        '- 200 秒作为所有允许场景的硬保证并不成立：10 个源均匀位于半径 1800 m 圆周时，即使预知所有位置并免去全部测量，移动与成功清除的下界已超过 233 秒/点。这个反例不否定某一随机场景分布下均值降至 200 秒的可能性。',
        '- 当前还没有找到能把完整普通场景均值降至 200 秒左右的策略；不能据有限搜索断言 200 秒的分布均值不可能。下一轮需要改善未知目标的发现时机和后续路径联动，继续微调现有阈值的收益有限。',
        '', '## 上一次真实演练复盘','',
        'M01 v02 的已保存演练与官方结束记录核对后为 14/14 全清，3854.08 秒，275.29 秒/点；移动 16020.42 米，占时间 83.13%。最后一个源清除之后还用了 561.90 秒排查未知频道，这部分必须纳入总时间。没有失败清除。证据归档在 ../m01-region-routing/runs/R005-official-practice-analysis/。不同真实案例的成绩不可直接当成同场景算法因果比较。',
        '', '本研究未修改团队 adopted、未提交或推送 Git。当前运行包是保留进展的研究候选，尚不是满足 200 秒验收线的最终方案。']
    (OUT/'研究进展与结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    trial_lines=['# 全部已完成试验比较','', '只对完整且无错误的整组给出有效均值；不同批次样本量不同，不直接按全表最小值选策略。','',
        '| 批次 | 变体 | 完整场景数/计划记录数 | 均值秒/点 |','|---|---|---:|---:|']
    for v in trials:trial_lines.append(f'| {v["run"]} | {v["variant"]} | {v["full"]}/{v["cases"]} | '+(f'{v["mean"]:.3f}' if v['eligible'] else '无效：有失败或未全清')+' |')
    trial_lines+=['','## 未完成或截断的批次','',json.dumps(invalid,ensure_ascii=False,indent=2)]
    (OUT/'trials.md').write_text('\n'.join(trial_lines)+'\n',encoding='utf-8')
    ordered={k:sorted([r for r in rows if r['variant']==k],key=lambda r:r['seed']) for k in LABELS}
    styles={'font.family':'Microsoft YaHei','font.size':10,'axes.spines.top':False,
            'axes.spines.right':False,'svg.fonttype':'none','axes.unicode_minus':False}
    with plt.rc_context(styles):
        fig,axes=plt.subplots(1,2,figsize=(11.6,4.8),layout='constrained')
        x=np.array([r['per_source_s'] for r in ordered['baseline']]);y=np.array([r['per_source_s'] for r in ordered[best]])
        axes[0].scatter(x,y,s=15,alpha=.65,c='#00699b',marker='o')
        lim=[min(x.min(),y.min())-15,max(x.max(),y.max())+15]
        axes[0].plot(lim,lim,color='#666666',ls='--',lw=1,label='相同耗时')
        axes[0].axhline(200,color='#a13800',ls=':',lw=1.5,label='200 秒/点目标')
        axes[0].set(xlim=lim,ylim=lim,xlabel='M01 旧版（秒/点）',ylabel=f'{LABELS[best]}（秒/点）',title='A  同一场景的配对结果（n=200）')
        axes[0].legend(frameon=False,loc='upper left',fontsize=9)
        for k,color,marker in [('baseline','#555555','s'),(best,'#00699b','o')]:
            ns=list(range(10,17));v=[by_n[k][n]['mean'] for n in ns]
            err=[by_n[k][n]['mean_ci95'][1]-by_n[k][n]['mean'] for n in ns]
            axes[1].errorbar(ns,v,yerr=err,color=color,marker=marker,capsize=3,label=LABELS[k],lw=1.5)
        axes[1].axhline(200,color='#a13800',ls=':',lw=1.5)
        axes[1].set(xlabel='实际目标数量 N',ylabel='场景均值（秒/点）',title='B  按目标数分层（均值 ± 95% t 区间）',xticks=range(10,17))
        axes[1].legend(frameon=False,fontsize=9)
        for ax in axes:ax.grid(alpha=.15)
        fig.savefig(OUT/'paired-comparison.png',dpi=200,facecolor='white')
        fig.savefig(OUT/'paired-comparison.svg',facecolor='white')
        plt.close(fig)
    provenance=dict(source=str(AUDIT/'results.json'),source_sha256=hashlib.sha256((AUDIT/'results.json').read_bytes()).hexdigest(),
        width_inches=11.6,height_inches=4.8,png_dpi=200,svg_text='editable; requires Microsoft YaHei',
        python=platform.python_version(),matplotlib=matplotlib.__version__,
        transformations=['T / actual N per completed scene','paired points: all 200 scenes, no filtering','stratified means with 95% Student t confidence intervals'],
        uncertainty_scope='Monte Carlo scene variation under the stated local generator, not official score uncertainty',
        destination='provisional CUMCM research figure; manuscript size/typesetting not finalized',
        alt_text='All 200 paired scene results compare the old strategy with the best observed frozen candidate. The second panel separates results by 10 through 16 sources. The candidate improves mean performance but its overall mean remains above the 200 second target.')
    (OUT/'figure-provenance.json').write_text(json.dumps(provenance,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(best=best,summary=summary,invalid=invalid),indent=2))


if __name__=='__main__':main()
