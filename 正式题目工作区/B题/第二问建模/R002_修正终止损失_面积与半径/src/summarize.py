"""Build separate objective records and a report from saved numerical outputs."""
from pathlib import Path
import csv,json,math,hashlib,platform,subprocess,datetime
ROOT=Path(__file__).resolve().parents[1]
def read(name):return list(csv.DictReader((ROOT/name).open()))
def writecsv(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 comp=read('verification/comparison.csv');lookup={r['name']:r for r in comp};near=read('results/nearopt5.csv');summary={}
 for name,col in [('area','J'),('radius','E_radius_loss')]:
  r={k:float(v) for k,v in lookup[name].items() if k!='name'}
  candidates=[a for a in near if float(a[col])<=1.01*r[col]]
  writecsv(ROOT/'results'/name/'candidates_1pct_grid5.csv',candidates)
  bounds={k:[min(float(a[k]) for a in candidates),max(float(a[k]) for a in candidates)] for k in ['x','y']}
  outcome={'objective':name,'objective_definition':'E[(1-T) pi rho^2]' if name=='area' else 'E[(1-T) rho]','point_north_m':[r['x'],r['y']],'point_south_m':[r['x'],-r['y']],'expected_area_loss_m2':r['J'],'expected_radius_loss_m':r['E_radius_loss'],'strong_probability':r['P_H'],'no_signal_probability':r['P_N'],'normal_bearing_probability':r['P_A'],'immediate_guaranteed_localization_probability':r['P_loc'],'distance_from_S1_m':math.hypot(r['x'],r['y']),'azimuth_deg':math.degrees(math.atan2(r['y'],r['x'])),'distance_to_first_support_m':r['y']*math.cos(math.pi/180)-r['x']*math.sin(math.pi/180),'nearoptimal_grid_step_m':5,'nearoptimal_grid_count':len(candidates),'nearoptimal_grid_bounds':bounds,'nearoptimal_note':'Bounding box only; use listed CSV points, not every point in the box. Reflections are equivalent. Classification uses level 3 integration.','verification':'numerical convergence, independent geometry, direct joint-prior rejection Monte Carlo','optimization_status':'best numerical candidate; no certified continuous global optimum'}
  (ROOT/'results'/name/'result.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n');summary[name]=outcome
 a=summary['area'];r=summary['radius'];comparison={'point_distance_m':math.dist(a['point_north_m'],r['point_north_m']),'radius_objective_reduction_percent':100*(1-r['expected_radius_loss_m']/a['expected_radius_loss_m']),'area_objective_increase_percent':100*(r['expected_area_loss_m2']/a['expected_area_loss_m2']-1)}
 summary['comparison']=comparison
 (ROOT/'results/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 checks=json.loads((ROOT/'verification/checks.json').read_text());geo=json.loads((ROOT/'verification/geometry_summary.json').read_text());strong=lookup['strong_example'];analytic=math.pi*25/(math.pi/180*((1500**3-1000**3)/(3*500)-25))
 (ROOT/'verification/strong_analytic_check.json').write_text(json.dumps({'q':[500,0],'C1_analytic':math.pi/180*((1500**3-1000**3)/(3*500)-25),'P_H_analytic':analytic,'P_H_numerical':float(strong['P_H']),'absolute_error':float(strong['P_H'])-analytic,'strong_branch_radius_m':5,'strong_branch_dmax_m':5,'strong_branch_area_loss':0,'strong_branch_radius_loss':0},indent=2))
 report=f'''# 第二检测点求解结果：修正终止损失，比较面积与半径目标

本轮沿用第一点 S₁=(0,0)、第一次正常示向度 0° 的基准情形。模型源文件见 `model/模型快照.tex`。源位置在半径1800米圆域内按面积均匀分布；有效接收半径在观测前服从 U[1000,1500]，与源位置独立；不同地点的角误差独立服从 U[-1°,1°]。第一次正常反馈同时更新源位置和固定接收半径，两次检测使用同一个接收半径。

## 两个目标及本次修正

反馈 z 后的可行位置集合为 K_z(q)，最小包围圆半径为 ρ_z(q)。定义 T_z(q)=1，当且仅当 max_{{g∈K_z(q)}}‖g−q‖≤20米。面积目标为 J_A(q)=E[(1−T_Z(q))πρ_Z(q)²]，半径目标为 J_R(q)=E[(1−T_Z(q))ρ_Z(q)]，两者都包含强信号、无信号和全部正常示向度反馈。

强信号表示源在 q 的5米范围内，故 T_H=1，两种损失均为零。正常反馈若使全部可行位置落在 q 的20米范围内，也取零损失。未终止反馈分别按面积或半径计损失。半径目标是期望半径，不是期望面积开方。两种目标均不包含移动时间，也未强制第二点保证接收。

本次同时修复了旧程序的清除条件指标。判断使用源到当前检测点 q 的最远距离，而非源到最小包围圆圆心的最远距离。旧版结果与代码保留在 R001 中。

## 结果

| 优化目标 | 北侧候选点（米） | 期望面积损失（平方米） | 期望半径损失（米） | 无信号概率 |
|---|---|---:|---:|---:|
| 最小期望面积 | ({a['point_north_m'][0]:.1f}, {a['point_north_m'][1]:.1f}) | {a['expected_area_loss_m2']:.4f} | {a['expected_radius_loss_m']:.6f} | {100*a['no_signal_probability']:.6f}% |
| 最小期望半径 | ({r['point_north_m'][0]:.1f}, {r['point_north_m'][1]:.1f}) | {r['expected_area_loss_m2']:.4f} | {r['expected_radius_loss_m']:.6f} | {100*r['no_signal_probability']:.6f}% |

关于 x 轴对称的南侧点具有相同目标值。表中坐标取0.1米展示精度，指标对应未舍入的优化坐标；舍入坐标的重新评价见 `verification/comparison.csv`。以上是全域网格与多起点细化得到的数值最优候选，尚无连续空间全局最优性证明。

两个北侧候选点相距 {comparison['point_distance_m']:.2f} 米。改用期望半径目标，将期望半径减少 {a['expected_radius_loss_m']-r['expected_radius_loss_m']:.6f} 米（{comparison['radius_objective_reduction_percent']:.4f}%），同时使期望面积增加 {r['expected_area_loss_m2']-a['expected_area_loss_m2']:.6f} 平方米（{comparison['area_objective_increase_percent']:.4f}%）。面积目标更重视较大半径反馈的平方损失，两个目标因此产生不同选点。

两点距第一次支持集分别约为 {a['distance_to_first_support_m']:.1f} 米、{r['distance_to_first_support_m']:.1f} 米，均超过20米，强信号概率与原地保证清除的概率均为0。因此在这两个点上，最新终止分支修正不改变损失；面积方案也几乎复现了旧点 (932.6,590)。本轮并未排除强信号候选：另加密搜索了扇形附近600个点，其最好面积约41997平方米，最好期望半径约98.42米，均明显劣于最终候选。此网格结果是数值证据，不是对全部近距离点的解析排除证明。

原地光学定位的测试点 (500,0) 的强信号概率约 {100*float(strong['P_H']):.6f}%，整体原地保证定位概率约 {100*float(strong['P_loc']):.4f}%，但期望面积约 {float(strong['J']):.0f} 平方米、期望半径约 {float(strong['E_radius_loss']):.2f} 米。它说明强信号分支已被正确奖励，同时其他反馈的较大定位区域仍会决定整体期望。

## 近优候选记录

两个 `results/<目标>/candidates_1pct_grid5.csv` 分别保存对应目标值不超过本次最优值101%的5米网格候选点。面积目标记录 {a['nearoptimal_grid_count']} 个北侧点，坐标范围为 x∈{a['nearoptimal_grid_bounds']['x']}、y∈{a['nearoptimal_grid_bounds']['y']}；半径目标记录 {r['nearoptimal_grid_count']} 个北侧点，坐标范围为 x∈{r['nearoptimal_grid_bounds']['x']}、y∈{r['nearoptimal_grid_bounds']['y']}。南侧由反射得到。这里给出的矩形只是候选点的坐标范围，实际候选以CSV中的点为准。

## 数值方法与验证范围

第一后验通过极坐标积分，面积元含径向因子 r。接收权重 w(d) 分段为1、(1500−d)/500、0；两次正常接收使用 w(max(d₁,d₂))，以保持同一个未知接收半径。几何区域由直线及圆弧精确构造；圆弧最远点用于检查连续区域的包围圆，内外半径界控制几何误差。对位置和反馈角度分段作 Gauss–Legendre 积分，并在几何变化与终止判据变化处细分。

利用南北对称性，在覆盖候选域的 [-1500,3000]×[0,1550] 外包矩形上先以50米网格搜索，筛选得到2381个可行点；另评估600个扇形邻近点。每个目标选择8个相互分离的起点作 Nelder–Mead 细化，再以更高积分精度细化最优点，最后独立提高积分精度评价。额外3111个5米网格点用于描述近优区域。网格和局部优化不构成全局最优证明。

最终两点的概率归一化误差最大为 {max(abs(c['mass_residual']) for c in checks.values()):.3g}；积分精度5级提升到6级后，面积变化最大为 {max(abs(c['area_level5_to6']) for c in checks.values()):.3g} 平方米，半径变化最大为 {max(abs(c['radius_level5_to6']) for c in checks.values()):.3g} 米。镜像点的面积差不超过 {max(abs(c['reflection_area_difference']) for c in checks.values()):.3g} 平方米。这些是固定候选点的数值精度检查，不代表优化坐标或全局最优性误差界。

独立几何核验采用极射线区间构造，不复用C++圆弧边界表示。共检查{geo['cases']}组反馈，独立可行点超出包围圆的最大数值残差为 {geo['max_sample_outside_m']:.3g} 米；独立采样直径给出的半径下界与主程序半径之差至多 {geo['max_radius_gap_m']:.6f} 米。该下界与有限采样的外包检查覆盖所列测试案例，不是全部反馈的独立证明。

每个最终候选另作250000次模拟：直接从源径向面积先验和接收半径均匀先验联合采样，按第一次正常接收条件拒绝不相容样本，再生成第二次反馈。它与主积分的尾概率加权路径不同。两目标的模拟均值与确定性积分相差均不足1个蒙特卡洛标准误，未出现真实源落在所计算支持集之外的情况。模拟中的包围圆仍由主程序计算，所以几何正确性另由前述独立方法核验。

测试点 (500,0) 的强信号分支支持集是完整5米圆盘，解析概率 π·25/C₁={analytic:.12f}；数值结果与其相差 {abs(float(strong['P_H'])-analytic):.3g}，该分支包围圆半径为5米而两种损失均为零。

## 文件与复现

- `results/area/result.json`、`results/radius/result.json`：分目标结果及指标定义。
- `results/area/best.json`、`results/radius/best.json`：优化器输出；`multistart.json` 记录8起点结果。
- `results/summary.json`：交叉评价与比较。
- `verification/`：积分收敛、反射对称、几何核验、随机验证及基线比较。
- `src/solver.cpp`：几何、积分、期望损失及模拟；`src/reproduce.py` 为复现入口。
- `manifest.yaml`：环境、来源哈希、运行命令与验证状态。

使用 Python 3（NumPy）及 C++17 编译器运行 `python3 src/reproduce.py`。本机应使用下述命令中的已配置Python。首次编译和搜索、验证通常耗时约数分钟，复现脚本总时间上限15分钟，命中上限会保存已完成输出并停止。本轮为本地候选研究记录，未提交、未推送，未修改团队正式采用入口。

## 待后续研究

清除条件概率目标及改进方案本次未作优化。后续应先统一成功事件：原地保证清除、真实源恰在光学范围内，或允许另选一个清除点，三者对应不同概率目标。若意图提高完成清除的机会，优化方向通常为最大化成功概率或最小化失败概率；再考虑以期望剩余半径等指标处理成功概率相同的候选点。本轮没有据此改变目标或选点。
'''
 (ROOT/'结果汇报.md').write_text(report)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
