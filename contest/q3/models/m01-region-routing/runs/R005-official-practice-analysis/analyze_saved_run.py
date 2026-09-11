"""Read-only analysis of saved simulator responses; never connects to an API.

Writes a NEW analysis directory with archived evidence, independent accounting,
LP checks of logged regions, route plots and a Chinese review.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import numpy as np
from scipy.optimize import linprog


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(run, check_regions=False):
    events = [json.loads(line) for line in (run / 'actions.jsonl').read_text(encoding='utf-8').splitlines()]
    requests, seen, histories, latest = {}, set(), defaultdict(list), {}
    p, current_channel, clock = (0., 0.), 1, 0.
    rows, phases, clears, certificates, regions = [], [], [], [], []
    no_signal = defaultdict(list)
    counts = Counter(e['kind'] for e in events)
    anchor_points = [(0., 0.)] + [(1350 * math.cos(i * math.pi / 3), 1350 * math.sin(i * math.pi / 3)) for i in range(6)]
    max_support_error = 0.
    lp_checks = 0
    pending_certificate = None
    for e in events:
        if e['kind'] == 'request':
            payload = e['payload']
            rid = payload['request_id']
            if rid in requests:
                assert requests[rid]['payload'] == payload
            requests[rid] = e
        elif e['kind'] == 'region':
            channel = e['channel']
            poly = np.asarray(e['vertices'])
            center = np.asarray(e['center'])
            assert np.max(np.linalg.norm(poly - center, axis=1)) <= e['radius_m'] + 1e-6
            if check_regions:
                angles = np.arange(180) * 2 * np.pi / 180
                normals = np.column_stack((np.cos(angles), np.sin(angles)))
                A, b = [normals], [np.full(180, 1800.)]
                for location, obs in histories[channel]:
                    location = np.asarray(location)
                    kind = obs['measure_result']
                    if kind == 'direction':
                        lower, upper = np.deg2rad([obs['svd_deg'] - 1.0051, obs['svd_deg'] + 1.0051])
                        rows_a = np.array([[math.sin(lower), -math.cos(lower)], [-math.sin(upper), math.cos(upper)]])
                        A.append(rows_a)
                        b.append(rows_a @ location)
                    radius = 5.000001 if kind == 'near' else 1500.000001
                    A.append(normals)
                    b.append(radius + normals @ location)
                A, b = np.vstack(A), np.concatenate(b)
                # Independent LP support calculation, no clipping or MEC code.
                for angle in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                    direction = np.array([math.cos(angle), math.sin(angle)])
                    sol = linprog(-direction, A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
                    assert sol.success, sol.message
                    discrepancy = abs(-sol.fun - np.max(poly @ direction))
                    assert discrepancy < 2e-5, discrepancy
                    max_support_error = max(max_support_error, discrepancy)
                    lp_checks += 1
            latest[channel] = e
            regions.append(dict(channel=channel, observation=len(histories[channel]), radius_m=e['radius_m'],
                                vertex_count=len(poly), x=p[0], y=p[1]))
        elif e['kind'] == 'clear_certificate':
            poly = np.asarray(latest[e['channel']]['vertices'])
            radius = float(np.max(np.linalg.norm(poly - e['point'], axis=1)))
            assert abs(radius - e['worst_distance_m']) < 1e-6 and radius <= 19.500001
            pending_certificate = e
            certificates.append(e)
        elif e['kind'] == 'response':
            if e['http_status'] != 200 or e['response'].get('accepted') is not True:
                counts['rejected_responses'] += 1
                continue
            rid = e['request_id']
            if rid in seen:
                counts['duplicate_accepted_responses'] += 1
                continue
            seen.add(rid)
            req, rsp = requests[rid], e['response']
            payload, path = req['payload'], req['path']
            point = tuple(payload['position'][a] for a in ('x', 'y')) if 'position' in payload else p
            channel = payload.get('channel')
            distance = math.dist(p, point)
            switch = int(path == '/measure' and channel != current_channel)
            result = rsp.get('measure_result', rsp.get('clear_result', rsp.get('exit_reason', '')))
            operating = 5 if path == '/measure' else (5 if result == 'success' else 3) if path == '/clear' else 0
            scan = path == '/measure' and min(math.dist(point, q) for q in anchor_points) < 1e-6
            if scan and (not phases or math.dist(point, phases[-1]['point']) > 1e-6):
                phases.append(dict(phase=len(phases) + 1, point=point, distance_m=0., time_s=0.,
                                   scan_measures=0, tracking_measures=0, cleared=[]))
            delta = rsp['virtual_time_s'] - clock
            row = dict(index=len(rows) + 1, path=path, channel=channel, x=point[0], y=point[1],
                       from_x=p[0], from_y=p[1], result=result, scan=scan, phase=len(phases),
                       distance_m=distance, movement_s=distance / 5, switch_s=switch,
                       operating_s=operating, delta_s=delta, virtual_time_s=rsp['virtual_time_s'],
                       accounting_error_s=delta - distance / 5 - switch - operating)
            assert abs(row['accounting_error_s']) < 2e-5, row
            rows.append(row)
            if phases:
                phase = phases[-1]
                phase['time_s'] += delta
                phase['distance_m'] += distance
                phase['scan_measures'] += int(scan)
                phase['tracking_measures'] += int(path == '/measure' and not scan)
            if path == '/measure':
                current_channel = channel
                if result == 'no_signal':
                    no_signal[channel].append(point)
                else:
                    histories[channel].append((point, rsp))
            if path == '/clear' and result == 'success':
                if check_regions:
                    assert pending_certificate is not None and pending_certificate['channel'] == channel
                    assert math.dist(point, pending_certificate['point']) < 1e-6
                    pending_certificate = None
                clears.append(row)
                phases[-1]['cleared'].append(channel)
            p, clock = point, rsp['virtual_time_s']
    assert len(seen) == len(requests)
    summary = read(run / 'summary.json')
    assert math.isclose(clock, summary['virtual_time_s'], abs_tol=1e-5)
    assert len(clears) == summary['cleared_count']
    assert sum(r['path'] == '/measure' for r in rows) == summary['measure_count']
    assert sum(r['result'] == 'no_target_in_range' for r in rows) == summary['clear_failures']
    source_checks = {}
    if (run / 'manifest.json').exists():
        for name, sha in read(run / 'manifest.json')['source_sha256'].items():
            source_checks[name] = digest(run / 'source_snapshot' / name) == sha
        assert all(source_checks.values())
    coverage_margins = {}
    if check_regions:
        h = 1800 / 128
        axis = np.linspace(-1800 + h, 1800 - h, 128)
        x, y = np.meshgrid(axis, axis)
        cells = np.column_stack((x.ravel(), y.ravel()))
        nearest = np.maximum(np.abs(cells) - h, 0)
        cells = cells[np.sum(nearest ** 2, axis=1) <= 1800 ** 2 + 1e-6]
        absent = summary['completion']['absent_channels']
        assert set(absent) | {r['channel'] for r in clears} == set(range(1, 21))
        for c in absent:
            assert not histories[c]
            positions = no_signal[c]
            bounds = [np.linalg.norm(np.abs(cells - q) + h, axis=1) for q in positions]
            worst = float(np.min(np.asarray(bounds), axis=0).max())
            assert worst <= 999.99
            coverage_margins[c] = 1000 - worst
    cost = dict(movement=sum(r['movement_s'] for r in rows), measurement=5 * summary['measure_count'],
                switching=sum(r['switch_s'] for r in rows), clear_success=5 * len(clears),
                clear_failure=3 * summary['clear_failures'])
    metrics = dict(counts=dict(counts), unique_actions=len(rows), source_hash_verified=source_checks,
                   virtual_time_s=clock, cost_s=cost, cleared_count=len(clears),
                   distance_m=sum(r['distance_m'] for r in rows), scan_count=sum(r['scan'] for r in rows),
                   tracking_count=sum(r['path'] == '/measure' and not r['scan'] for r in rows),
                   measure_results=dict(Counter(r['result'] for r in rows if r['path'] == '/measure')),
                   max_accounting_error_s=max(abs(r['accounting_error_s']) for r in rows),
                   last_clear_time_s=clears[-1]['virtual_time_s'], tail_s=clock - clears[-1]['virtual_time_s'],
                   phases=phases, independent_lp_checks=lp_checks, max_lp_support_error_m=max_support_error,
                   clear_certificates_checked=len(certificates), absent_coverage_margin_m=coverage_margins)
    return metrics, rows, regions, summary


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--official', type=Path, required=True)
    parser.add_argument('--old-runs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    evidence = args.output / 'evidence'
    evidence.mkdir()
    stem = args.official.name.removesuffix('.result.json')
    evidence_sources = [args.run / 'summary.json', args.run / 'manifest.json', args.run / 'actions.jsonl']
    evidence_sources += [args.official.with_name(stem + suffix) for suffix in ('.result.json', '.jlog', '.psum')]
    for p in evidence_sources:
        shutil.copy2(p, evidence / p.name)
    shutil.copy2(__file__, args.output / 'analyze_saved_run.py')
    official = read(args.official)
    metrics, rows, regions, summary = replay(args.run, check_regions=True)
    assert official['jammer_count'] == metrics['cleared_count']
    assert official['problem_no'] == 3 and official['directional_jammer_count'] == 0
    metrics['official_result'] = official
    (args.output / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(args.output / 'actions.csv', rows)
    write_csv(args.output / 'regions.csv', regions)
    per_target = []
    for clear in [r for r in rows if r['result'] == 'success']:
        c = clear['channel']
        hist = [r for r in regions if r['channel'] == c]
        related = [r for r in rows if r['channel'] == c and not r['scan']]
        per_target.append(dict(channel=c, positive_observations=len(hist),
                               radii_m=' -> '.join(f'{r["radius_m"]:.2f}' for r in hist),
                               follow_distance_m=sum(r['distance_m'] for r in related),
                               clear_time_s=clear['virtual_time_s']))
    write_csv(args.output / 'targets.csv', per_target)
    comparisons = []
    for run in sorted(args.old_runs.iterdir()):
        if not (run / 'summary.json').exists():
            continue
        met, _, _, old = replay(run)
        comparisons.append(dict(run=run.name, cleared=old['cleared_count'],
                                time_s=old['virtual_time_s'], average_s=old['average_clear_time_s'],
                                distance_m=met['distance_m'], measures=old['measure_count'],
                                failures=old['clear_failures']))
    comparisons.append(dict(run=args.run.name, cleared=summary['cleared_count'], time_s=summary['virtual_time_s'],
                            average_s=summary['average_clear_time_s'], distance_m=metrics['distance_m'],
                            measures=summary['measure_count'], failures=summary['clear_failures']))
    write_csv(args.output / 'historical-comparison.csv', comparisons)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, (ax, progress) = plt.subplots(1, 2, figsize=(12.5, 5.4), constrained_layout=True)
    ax.add_patch(plt.Circle((0, 0), 1800, fill=False, color='gray', ls='--'))
    for r in rows:
        if r['distance_m'] > 1e-5:
            ax.plot([r['from_x'], r['x']], [r['from_y'], r['y']],
                    color='#d97706' if r['scan'] else '#267ca3', alpha=.6, lw=1.1)
    for phase in metrics['phases']:
        p = phase['point']
        ax.scatter(*p, marker='s', color='#222222', s=25)
        ax.annotate(f'S{phase["phase"]}', p, xytext=(5, 5), textcoords='offset points', fontsize=8)
    clear_rows = [r for r in rows if r['result'] == 'success']
    ax.scatter([r['x'] for r in clear_rows], [r['y'] for r in clear_rows], color='#16834b', s=25)
    for r in clear_rows:
        offset = (4, -12) if r['channel'] in (9, 3, 11) else (4, 4)
        ax.annotate(str(r['channel']), (r['x'], r['y']), xytext=offset, textcoords='offset points', fontsize=8)
    ax.set(aspect='equal', xlabel='East (m)', ylabel='North (m)', title='Saved route: orange = travel to scan sites\nGreen = clear positions (not source truth)')
    times = [0] + [r['virtual_time_s'] / 60 for r in clear_rows] + [metrics['virtual_time_s'] / 60]
    progress.step(times, [0] + list(range(1, len(clear_rows) + 1)) + [len(clear_rows)], where='post', color='#16834b')
    progress.axvspan(metrics['last_clear_time_s'] / 60, metrics['virtual_time_s'] / 60,
                    color='#d97706', alpha=.15, label='Remaining coverage verification')
    progress.set(xlabel='Virtual time (min)', ylabel='Cleared sources', ylim=(0, 15),
                 title=f'Official case {official["case_code"]}\n14/14 cleared; 99 measurements; 0 failed clears')
    progress.grid(alpha=.2)
    progress.legend(fontsize=8)
    fig.savefig(args.output / 'route-and-progress.png', dpi=180)
    fig.savefig(args.output / 'route-and-progress.svg')
    plt.close(fig)
    phases = metrics['phases']
    time_s = metrics['virtual_time_s']
    text = ['# 问题三改进策略首次实际演练复盘', '',
        f'案例：{official["case_code"]}；程序运行目录：{args.run.name}；分析日期：2026-09-11。', '',
        f'结论：官方 result.json 确认场内 14 个全向源，动作响应确认成功清除 14 个，零失败，正常 user_exit。总虚拟耗时 {time_s:.6f} s，平均每源 {time_s/14:.6f} s，累计移动 {metrics["distance_m"]:.3f} m；本地脚本墙钟 1.75 s。', '',
        '官方结果文件只提供案例与真实总数，不含逐源真位置，也不单独提供成绩总时间；耗时来自保存的官方 API 响应，已按原始动作独立重算。没有解密 .jlog/.psum，没有连接或重新运行模拟器。', '',
        '## 结果核对', '',
        f'- 115 个唯一动作：enter 1、measure 99、clear 14、exit 1；115 请求和115响应，均一次接受，没有重试、拒绝或未确认动作。',
        f'- 4 份当场源码哈希与 manifest 一致。逐动作时间守恒最大偏差 {metrics["max_accounting_error_s"]:.3g} s，符合响应小数舍入。',
        f'- 重建39次正观测的完整约束，对每个区域做16方向 LP 支持函数检查，共 {metrics["independent_lp_checks"]} 项；最大差异 {metrics["max_lp_support_error_m"]:.3g} m。14次清除点都通过顶点最坏距离复核。',
        f'- 未发现的频道2、5、6、7、19、20均有7个测站的真实 no_signal 记录；从动作记录重新构造的整格覆盖最小半径余量 {min(metrics["absent_coverage_margin_m"].values()):.3f} m。不是仅相信 summary 中的完成标志。', '',
        '## 时间花在哪里', '', '| 项目 | 虚拟时间/s | 占比 |', '|---|---:|---:|']
    labels = {'movement':'移动', 'measurement':'99次检测', 'switching':'85次检测频道切换', 'clear_success':'14次成功清除', 'clear_failure':'清除失败'}
    text += [f'| {labels[k]} | {v:.3f} | {v/time_s:.2%} |' for k,v in metrics['cost_s'].items()]
    text += ['', '按动作用途分，扫描点检测74次、专门定位检测25次。39次正观测中包含14次首次发现，其余25次为定位补测；14个源平均新增1.79次定位检测。由此看，继续减少测量次数的直接收益有限，路线仍然是主要优化对象。', '',
        '## 七个阶段', '', '| 顺序 | 测站坐标/m | 清除频道 | 扫描/定位检测次数 | 路程/m | 总时间/s |', '|---|---|---|---:|---:|---:|']
    for s in phases:
        text.append(f'| {s["phase"]} | ({s["point"][0]:.0f}, {s["point"][1]:.0f}) | {", ".join(map(str,s["cleared"])) or "无"} | {s["scan_measures"]}/{s["tracking_measures"]} | {s["distance_m"]:.1f} | {s["time_s"]:.2f} |')
    text += ['', '阶段按实际访问顺序划分，包含到该扫描站的移动、在站检测及该站发现目标的定位清除，不将这些总时间误称为纯定位时间。', '',
        f'最后一个源在 {metrics["last_clear_time_s"]:.3f} s 清除；之后用了 {metrics["tail_s"]:.3f} s（全程 {metrics["tail_s"]/time_s:.2%}）完成余下两个测站、12次无信号检测。该段不是可以直接删掉的浪费：程序当时不知道总数为14，还需排除其他频道。第四站也没有发现新源，但其无信号记录参与完整覆盖。', '',
        '## 前两问的方法在实际接口上是否成立', '',
        '- 区域交会起效：频道4从750.14 m缩至16.33 m，仅增加一次检测就可清除；频道11最终半径19.41 m，也在19.5 m余量内完成。',
        '- 较难的频道14、12、1、3各有3次补测。例如频道3半径750.17→48.62→20.94→约5 m；20.94 m时没有冒险使用20 m清除判据。',
        '- 25次专门定位测量全部收到 direction 或 near，没有在保证接收点丢信号；14次可靠清除全部成功。这是本局对实现的支持，不证明所有误差场和所有案例都无失败。',
        '- 末次near的频道16、3原地清除，其余安全点的最坏距离约19.5 m。清除位置是距真源20 m内的位置，图中的绿点不能当作真实干扰源坐标。', '',
        '## 与旧演练的比较', '', '| 运行 | 已清除 | 总虚拟时间/s | 每源平均/s | 路程/km | 检测数 | 清除失败 |', '|---|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:
        text.append(f'| {r["run"]} | {r["cleared"]} | {r["time_s"]:.2f} | {r["average_s"]:.2f} | {r["distance_m"]/1000:.3f} | {r["measures"]} | {r["failures"]} |')
    first, second = comparisons[:2]
    text += ['', f'相对第一局14源旧演练，总时间低 {1-time_s/first["time_s"]:.2%}，路程少 {1-metrics["distance_m"]/first["distance_m"]:.2%}；相对第二局16源旧演练，每源平均时间低 {1-summary["average_clear_time_s"]/second["average_s"]:.2%}。这三局案例不同，目标数相同也不代表场景相同，不能将这些差值作为策略因果提速或直接替代同案例配对。', '',
        '## 下一步分析优先级（本轮不改策略）', '',
        '1. 优先联合安排“补充观测点—处理目标—下一搜索站”，而不是只按当前包围圆中心排序。本局频道18的一次定位移动达1322.35 m；它在第一站最后处理，随后又到附近第二站扫描，值得检查能否把已知目标定位与测站访问合并。任何替代点须继续核对接收和信息增益，不能假设新测点会得到现有日志的同一读数。',
        '2. 面向未覆盖区域选择下一测站，并把必要的剩余频道检测安排在已有路径上。目标是减少搜索证明所需的额外路程，不是删除覆盖证明。此前全量机会扫描已在合成消融中增时；应测试更有针对性的规则，不能仅凭本局就重新打开。',
        '3. 通过相同案例的新旧策略配对检验效果，再谈参数微调或稳定提升比例。本轮不启动新演练，也不从已加密的官方日志臆造反事实目标位置。', '',
        '局限：这是一局实际演练成功，不是正式测试成绩或普遍最优证明。仍需保留近源聚集样例劣化、有限定位步数没有普遍完成证明等已有风险。', '',
        '![实际轨迹与清除进度](route-and-progress.png)', '',
        '证据：evidence/ 保存当场可读日志、摘要、manifest及官方结果/.jlog/.psum，附SHA-256。官方目录会随后续运行改变，报告以本分析目录冻结副本为准；源码仍使用当场 source_snapshot。']
    (args.output / '演练复盘.md').write_text('\n'.join(text), encoding='utf-8')
    manifest = dict(command=sys.argv, source_run=str(args.run), official_result_source=str(args.official),
                    data_type='actual_practice_API_responses_and_official_result_metadata',
                    no_new_simulator_requests=True, source_hashes={str(p):digest(p) for p in evidence_sources},
                    analyzer_sha256=digest(Path(__file__)), python=sys.version)
    (args.output / 'analysis-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
