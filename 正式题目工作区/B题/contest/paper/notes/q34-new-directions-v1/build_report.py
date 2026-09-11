"""Build research reports from retained same-scene results, including regressions."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[4]
Q3=ROOT/'contest/q3/models/m05-action-value'
Q4=ROOT/'contest/q4/models/m02-adaptive-cover'


def paired(run,baseline,candidate,q):
    rows=json.loads((run/'results.json').read_text(encoding='utf-8'))
    key,metric=('variant','per_source_s') if q==3 else ('policy','average_s')
    groups=[{r['seed']:r for r in rows if r[key]==name} for name in [baseline,candidate]]
    assert set(groups[0])==set(groups[1])
    for group in groups:
        assert all((r['full'] if q==3 else r['all_cleared']) and not r['error'] for r in group.values())
    seeds=sorted(groups[0]);values=[np.array([g[s][metric] for s in seeds]) for g in groups]
    d=values[0]-values[1];half=float(t.ppf(.975,len(d)-1)*np.std(d,ddof=1)/np.sqrt(len(d)))
    result=dict(run=str(run.relative_to(ROOT)),cases=len(d),baseline=baseline,candidate=candidate,
                baseline_s=float(values[0].mean()),candidate_s=float(values[1].mean()),saving_s=float(d.mean()),
                improvement_percent=float(100*d.mean()/values[0].mean()),ci95_s=[float(d.mean()-half),float(d.mean()+half)],
                improved=int(np.sum(d>1e-7)),worse=int(np.sum(d< -1e-7)),unchanged=int(np.sum(abs(d)<=1e-7)),
                worst_seed=int(seeds[int(np.argmin(d))]),worst_saving_s=float(d.min()),
                baseline_distance_m=float(np.mean([r['distance_m'] for r in groups[0].values()])),
                candidate_distance_m=float(np.mean([r['distance_m'] for r in groups[1].values()])),
                baseline_measures=float(np.mean([r['measures'] for r in groups[0].values()])),
                candidate_measures=float(np.mean([r['measures'] for r in groups[1].values()])),
                candidate_failures=float(np.mean([r['failures' if q==3 else 'failed_optical_attempts'] for r in groups[1].values()])),
                max_compute_s=float(max(r['compute_s' if q==3 else 'wall_s'] for r in groups[1].values())))
    return result


def trials(root,q):
    lines=['| 运行 | 策略 | 执行数 | 全清且无执行错误 | 均值秒/点 |','|---|---|---:|---:|---:|'];total=0
    key,metric=('variant','per_source_s') if q==3 else ('policy','average_s')
    for run in sorted((root/'runs').iterdir()):
        path=run/'results.json'
        if not path.exists():continue
        rows=json.loads(path.read_text(encoding='utf-8'));total+=len(rows)
        for name in dict.fromkeys(r[key] for r in rows):
            group=[r for r in rows if r[key]==name];n=sum(bool((r['full'] if q==3 else r['all_cleared']) and not r['error']) for r in group)
            value=f"{np.mean([r[metric] for r in group]):.4f}" if n==len(group) else '无有效全清均值'
            lines.append(f'| {run.name} | {name} | {len(group)} | {n} | {value} |')
    return '\n'.join(lines),total


def table(items):
    lines=['| 测试组 | 场数 | 原版秒/点 | 新版秒/点 | 平均节省秒/点 |','|---|---:|---:|---:|---:|']
    for title,r in items:
        lines.append(f"| {title} | {r['cases']} | {r['baseline_s']:.2f} | {r['candidate_s']:.2f} | {r['saving_s']:.2f} |")
    return '\n'.join(lines)


def main():
    a=paired(Q3/'runs/R004-frozen-audit','v5','v6',3)
    ab=paired(Q3/'runs/R005-failure-update-ablation','no_update','v6',3)
    ap=[(name,paired(Q3/'runs'/run,'v5','v6',3)) for name,run in
        [('边界等布局/+1度','R006-edge-plus'),('边界等布局/-1度','R007-edge-minus'),('随机布局/棋盘误差','R008-random-checker')]]
    b=paired(Q4/'runs/R006-frozen-audit','directional_v1','polar22',4)
    bp=[(name,paired(Q4/'runs'/run,'directional_v1','polar22',4)) for name,run in
        [('边界外向/+1度','R007-outward'),('边界切向/-1度','R008-tangent'),('近源聚集/棋盘误差','R009-cluster'),
         ('N-1个定向源','R010-mostly-directional'),('1个定向源','R011-mostly-omni')]]
    ta,na=trials(Q3,3);tb,nb=trials(Q4,4)
    summary=dict(q3=a,q3_ablation=ab,q3_pressure=dict(ap),q4=b,q4_pressure=dict(bp),
                 q3_executions=na,q4_executions=nb,official_results=False,target_200_achieved=False)
    out=Path(__file__).parent
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    text=f'''# 第三、四问新方向实施与冻结验证

2026-09-11。本轮第三问得到小幅主分布改善，第四问覆盖布局有明显提升。第三问200秒/点目标仍未达成。所有数字为本地同场配对结果，计入整场末尾排除和失败清除费用；不是官方演练或正式成绩。未提交推送，未改变团队adopted或全队STATUS。

{table([('第三问/60场留出',a),('第四问/40场留出',b)])}

## 第三问：光学动作评价可保留为候选，尚未突破瓶颈

v6使用试清成功/失败两种结果的时间评价，并把失败的20米排除信息作为非凸区域保留。全部{a['cases']}/{a['cases']}清除，节省{a['saving_s']:.4f}秒/点（{a['improvement_percent']:.3f}%），配对近似95% t区间[{a['ci95_s'][0]:.4f}, {a['ci95_s'][1]:.4f}]。{a['improved']}场改善、{a['worse']}场退化，最差种子{a['worst_seed']}增加{-a['worst_saving_s']:.4f}秒/点。

每场平均路程{a['baseline_distance_m']:.2f}→{a['candidate_distance_m']:.2f}米，检测{a['baseline_measures']:.2f}→{a['candidate_measures']:.2f}次，新版平均失败光学尝试{a['candidate_failures']:.2f}次，费用均已计入。主审计新版单场最大计算时间{a['max_compute_s']:.2f}秒（实际并行进程负载下测得）。

20场消融中，不更新失败区域为{ab['baseline_s']:.4f}，更新为{ab['candidate_s']:.4f}秒/点，差仅{ab['saving_s']:.4f}，区间[{ab['ci95_s'][0]:.4f}, {ab['ci95_s'][1]:.4f}]。因此不能把整体提速归因于失败信息更新单项；它在几何上有效，但效率贡献未证实。

{table(ap)}

上述压力均全清；极端误差组略慢，棋盘误差组几乎相同。v6的效率优势不能推广到未知官方误差场。新的剩余时间补测及融合在选择集229.7412秒/点，比v5的229.3784略慢，未采用。完整的停靠点/频道/未来全场路线联合优化仍未实现，本轮实现的是局部完成费用近似。

几何检查包含120个矩形区域、22472个直接距离筛选点，以及60组连续失败后再测向的保留检查。逐动作独立审核主审计与消融160次执行、21790个动作，压力40次执行、5732个动作。完成覆盖由内接1000米排除圆盘的并集重新检查，与原方格判定路径不同。

## 第四问：22点覆盖替代31点网格

覆盖点为中心1点、半径980米内圈7点、半径1850米外圈14点。位置只由题目几何构造，未使用源真值或随机种子。1334个子区域覆盖外切场地多边形，并依据实际无信号站点的凸包及1000米距离条件判断排除。继承v1的定位、保证清除和光学兜底。

40场新留出中均全清，节省{b['saving_s']:.4f}秒/点（{b['improvement_percent']:.2f}%），配对近似95% t区间[{b['ci95_s'][0]:.4f}, {b['ci95_s'][1]:.4f}]。{b['improved']}场改善、{b['worse']}场退化。**最差种子{b['worst_seed']}退化{-b['worst_saving_s']:.2f}秒/点**，该场N=16，原策略较早发现全部频道并停止搜索，表明更少的保底覆盖站不保证每个场景更快。

平均路程{b['baseline_distance_m']:.2f}→{b['candidate_distance_m']:.2f}米，检测{b['baseline_measures']:.2f}→{b['candidate_measures']:.2f}次。主审计新版单场最大计算时间{b['max_compute_s']:.2f}秒。

{table(bp)}

以上48场压力/类型比例测试与主40场均完整清除。独立审核使用实际无信号点、凸包半空间、逐顶点距离与场地分区并集，另重算每个动作的时间。源生成分布依然是本地设定，压力均值不混入主均值。覆盖构造的数值核验不等于策略全局最优或任意布局效率保证。

31点上仅改证明、额外清除点扫描、目标位置报价未获得收益，均保留。19/21等更少点的候选构造未通过当前几何条件；不能据此证明所有更少点布局都不可能。25点通过几何但选择集效率低于22点，保留为备选。

## 复现与写作入口

- 第三问：`contest/q3/models/m05-action-value/README.md`、`formulations/v01.md`、`verification/selection-v06.md`。
- 第四问：`contest/q4/models/m02-adaptive-cover/README.md`、`formulations/v01.md`、`verification/selection-v02.md`。
- 每轮运行保留配置、场景、源码快照及散列、逐动作；本轮共第三问{na}次、第四问{nb}次研究执行，不以失败光学尝试为理由删场。
- 运行目录：`D:/math modeling/正式题目工作区/B-simulator/p3-action-value-research`、`p4-adaptive-cover-research`；均完成离线自检，新版未调用官方接口。
- 推导引用：往年研读专题及本地论文03/09。迁移部分与本轮独立几何推导分开记录；不沿用旧论文不适配的免费检测、随机噪声或真值信息。

下一步优先解决第三问大尺度转场与定位任务的联合选择，以及第四问N=16等场景的提前发现顺序；不继续把不稳定的局部补测近似作为已有效模块叠加。
'''
    (out/'本轮优化报告.md').write_text(text,encoding='utf-8')
    for model,trial_text,stats in [(Q3,ta,a),(Q4,tb,b)]:
        (model/'verification/trials.md').write_text('# 本轮全部计算运行\n\n'+trial_text+'\n',encoding='utf-8')
        (model/'verification/summary.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
