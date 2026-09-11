"""Build traceable offline tables, figure and delivery inventory; no simulator."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as stats
import subprocess
import sys
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

MODEL = Path(__file__).resolve().parents[1]
REPO = MODEL.parents[3]


def main():
    files = {name: MODEL / 'runs' / name / 'results.json' for name in ('R002-paired', 'R003-final', 'R004-holdout')}
    data = {name: json.loads(p.read_text(encoding='utf-8')) for name, p in files.items()}
    def summarize(rows):
        return dict(cases=len(rows), full_clear=sum(r['full_clear'] and r['error'] is None for r in rows),
                    mean_time_s=stats.mean(r['virtual_time_s'] for r in rows),
                    mean_distance_m=stats.mean(r['distance_m'] for r in rows),
                    mean_measures=stats.mean(r['measures'] for r in rows),
                    clear_failures=sum(r['clear_failures'] for r in rows),
                    max_local_planning_s=max(r['elapsed_s'] for r in rows))
    table = []
    for name in ('R003-final', 'R004-holdout'):
        for variant in ('baseline', 'improved'):
            table.append(dict(run=name, variant=variant, **summarize([r for r in data[name] if r['variant'] == variant])))
    with (MODEL / 'verification' / 'paired-summary.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    holdout = data['R004-holdout']
    b = [r for r in holdout if r['variant'] == 'baseline']
    v = [r for r in holdout if r['variant'] == 'improved']
    reduction = 1 - stats.mean(r['virtual_time_s'] for r in v) / stats.mean(r['virtual_time_s'] for r in b)
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    ax.scatter([r['virtual_time_s'] for r in b], [r['virtual_time_s'] for r in v], s=24, color='#176b87', alpha=.75)
    ax.plot([2500, 8500], [2500, 8500], '--', color='#777777', linewidth=1, label='Equal time')
    ax.set(xlabel='Baseline virtual time (s)', ylabel='Improved v2 virtual time (s)',
           title='100 paired synthetic holdout scenes\nNot official simulator results', xlim=(2500, 8500), ylim=(2500, 8500))
    ax.grid(alpha=.15)
    ax.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(MODEL / 'verification' / 'holdout-comparison.png', dpi=180)
    fig.savefig(MODEL / 'verification' / 'holdout-comparison.svg')
    plt.close(fig)
    allv = [r for name in ('R003-final', 'R004-holdout') for r in data[name] if r['variant'] == 'improved']
    r003b = {r['index']: r for r in data['R003-final'] if r['variant'] == 'baseline'}
    worse = [r for r in data['R003-final'] if r['variant'] == 'improved' and r['virtual_time_s'] > r003b[r['index']]['virtual_time_s']]
    lines = ['# P3 v2 离线验证报告', '',
        '日期：2026-09-11。验证状态：离线世界与本地接口检查通过；采用状态：候选，待用户官方演练。', '',
        '所有场景均为本地构造，规划器只能取得仿 API 测量，真值仅供独立计时和正确性断言。这里没有连接官方 2026 端口、登录账号或生成官方成绩。', '',
        '| 批次 | 策略 | 全清场景 | 平均虚拟时间/s | 平均路程/m | 平均测量数 | 清除失败总数 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for row in table:
        lines.append(f"| {row['run']} | {row['variant']} | {row['full_clear']}/{row['cases']} | {row['mean_time_s']:.2f} | {row['mean_distance_m']:.2f} | {row['mean_measures']:.2f} | {row['clear_failures']} |")
    lines += ['', f'留出集的平均总虚拟耗时降低 {reduction:.2%}，100/100 场均较旧策略快。这个百分比是相同场景的平均总时间之比，不是官方平均清除时间的保证。', '',
        'R003 包括均匀圆域的 30 场固定位置正弦误差、30 场恒正/恒负/棋盘式 ±1° 误差，以及 16 场边界、近原点、近共线聚集及接收半径 1000 m 等构造。R004 固定最终参数后使用 seeds 30–129 的另外 100 场；R003 的主要随机种子为 0–29。留出误差仍为固定位置正弦误差，因此不覆盖所有允许的误差场。', '',
        f"最终版 176 场共核对 {sum(r['region_checks'] for r in allv)} 个观测区域的真值包含关系、{sum(r['clear_checks'] for r in allv)} 个清除证书。区域断言用多边形有向边叉积，独立于测向半平面生成；清除用真值距离与接口独立判断。检查无错误排除实际频道。", '',
        '几何反例：边长 38 m 等边三角形 D=38 m，但最小包围半径 21.9393102292 m；程序拒绝据 D≤40 清除。七测站使 13104 个完整保留方格全部被半径 999.99 m 覆盖；只在原点检测则不会错误证明全域覆盖。另检查 0/360° 跨界和舍入端点。', '',
        f'七测站连续几何参照最坏最近距离：{math.sqrt(1800**2+1350**2-2*1800*1350*math.cos(math.pi/6)):.6f} m。证书对应整格最大角点距离，不是网格中心抽查。', '',
        '4 项本地 HTTP 测试通过，见 client-test-output.txt：丢响应重试同 ID/同字节；明确拒绝不重置时钟/位置；畸形响应可重试、clear 不改变检测频道；不确定状态停止新动作。第四项以完整命令行程序连接随机本地端口上的独立世界，实际覆盖 enter→measure/clear→exit、源码快照、summary 和移动/切换统计。测试脚本共 4 个测试方法，其中一个方法组合检查多个行为。', '',
        '消融与未解决问题：', '',
        '- 开发前 10 场：关闭机会扫描 4075.59 s，开启 4489.42 s，故交付版默认关闭。固定编号顺序 4848.50 s，比相同 10 场最终版更慢。',
        f'- R003 中 {len(worse)} 场比旧策略慢：索引 '+', '.join(str(r['index']) for r in worse)+'。均为距离原点约 5.001 m 的 10 源聚集构造，首测不触发 near，中部侧向探测的步幅过大。这说明本版并非逐场支配旧策略。',
        '- 单目标 16 步预算内全误差情形的完成性未经证明；若不能收敛则明确未完成退出，不宣称成功。',
        '- 圆和角域保守外包、清除与接收余量降低浮点风险，但不是区间算术的机器可验证证明。',
        '- 程序在独立本地世界中的规划时间每场不足 0.14 s；不含完整 HTTP 与磁盘日志成本，官方真实时间需要实际演练。', '',
        '复现：在仓库根目录执行 verification/verify.py（完整相对路径见各 run/manifest.json 中 command），使用同目录 source_snapshot/simple_robot.py 作为冻结基线。结果输出目录必须为新目录，不能覆盖已有 R001–R004。依赖 numpy 2.2.6、scipy 1.15.3；报告另需 matplotlib。', '',
        'R001 是开发小样例；其 manifest 中 triangle_radius 因当时报告变量复用记录了后续例子的半径，三角形拒绝清除断言本身通过。此记录不作为最终数字来源；R002 以后已修正，保留原始记录和快照。', '',
        '![配对留出场景](holdout-comparison.png)', '']
    (MODEL / 'verification' / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    q1 = REPO / 'contest/q1/models/m01-bounded-bearing/src/bearing_geometry.py'
    assert q1.read_bytes() == (MODEL / 'src/bearing_geometry.py').read_bytes()
    tracked = list((MODEL / 'src').glob('*')) + list((MODEL / 'verification').glob('*')) + list((MODEL / 'formulations').glob('*'))
    inventory = {str(p.relative_to(MODEL)): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked if p.is_file() and p.name != 'inventory.json'}
    (MODEL / 'verification' / 'inventory.json').write_text(json.dumps(dict(
        source_base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        dirty_worktree=True, git_save_level='local_only_not_committed_not_pushed',
        q1_source=str(q1), q1_source_sha256=hashlib.sha256(q1.read_bytes()).hexdigest(),
        upstream_q2='contest/q2/models/m01-reception-minimax/formulations/v01.md',
        python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
        matplotlib=matplotlib.__version__, files_sha256=inventory), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Report built; holdout reduction {reduction:.2%}; {len(allv)} final-version cases.')


if __name__ == '__main__':
    main()
