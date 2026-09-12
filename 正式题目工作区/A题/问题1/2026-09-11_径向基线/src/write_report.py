from pathlib import Path
import json,hashlib,platform,subprocess,datetime,csv
import numpy as np,openpyxl
p=Path(__file__).resolve().parents[1]
s=json.loads((p/'results/selection.json').read_text());v=json.loads((p/'verification/checks.json').read_text())
T=s['sources']['T'];C=s['sources']['C'];a=np.loadtxt(p/'results/full_precision.csv',delimiter=',',skiprows=1)
def tbl(col):
 lines=['| 时间 / s | r=0 cm | r=0.5 cm | r=1 cm | r=1.5 cm | r=2 cm |','|---:|---:|---:|---:|---:|---:|']
 for t in [100,300,600,900,1200,1500,1800]:lines.append('| '+str(t)+' | '+' | '.join(f'{a[t,col+j]:.4f}' for j in [0,5,10,15,20])+' |')
 return '\n'.join(lines)
lines=['| 检查 | 温度最大差 / °C | 含水率最大差 / (kg/kg) |','|---|---:|---:|']
for label,d in [('时间步整套减半','time'),('空间网格加倍','space')]:lines.append(f"| {label} | {v['comparisons'][f'T_{d}_final_T']['max_difference']:.8e} | {v['comparisons'][f'C_{d}_final_C']['max_difference']:.8e} |")
roundcounts={f:len({(r['time_s'],r['radius_cm']) for r in []}) for f in ['T','C']}
with (p/'verification/rounding_disagreements.csv').open() as f:roundrows=list(csv.DictReader(f))
roundcounts={f:len({(r['time_s'],r['radius_cm']) for r in roundrows if r['field']==f}) for f in ['T','C']}
text=f'''# A题第一问计算与核验记录

## 本轮结论与范围

已使用附件1和附录2，完成已讨论的径向基线模型 M01-v01 在 0—1800 s 内的计算。结果属于研究分支上的候选计算成果，未标记为团队正式采用。未求解第二至第四问，未使用优秀论文的现成解答。

两场各输出 1800 个时刻、21 个径向位置，共 75,600 个结果值。`results/result1.xlsx` 按附件3的两个工作表组织，表头半径单位为 cm，A列时间单位为 s；最终单元格数值取四位小数。`results/full_precision.csv` 保留全部双精度值并额外包含 t=0 初值，是未舍入结果的唯一合并来源。不同网格结果均保存在 `runs/`，最终结果没有使用外推或裁剪。

1800 s 时，轴心和表面温度分别为 **{T['center_at_1800']:.4f} °C**、**{T['surface_at_1800']:.4f} °C**，轴心和表面干基含水率分别为 **{C['center_at_1800']:.4f} kg/kg**、**{C['surface_at_1800']:.4f} kg/kg**。按圆柱截面权重计算的平均温度为 {T['weighted_mean_at_1800']:.6f} °C，平均干基含水率为 {C['weighted_mean_at_1800']:.6f} kg/kg；相对于初始平均含水率，水分质量减少比例为 {s['moisture_mean_fraction_lost']*100:.4f}%。后一个比例使用恒定干物质质量假设，不需要把题给密度额外解释为干物质密度。

## 必须随结果保留的物理假设

[已确定假设] 药材状态仅随径向位置和时间变化，忽略端面造成的高度差异。半径为 0.02 m，轴心为 r=0，圆柱侧表面为 r=0.02 m。

[建模约定及补充闭合假设] 几何和干物质骨架固定，初始状态空间均匀；使用题给常数 rho=820 kg/m³、cp=2600 J/(kg·K)、k=0.36 W/(m·K)、h=25 W/(m²·K)、hm=8e-7 m/s 及 D(C)=7e-9 exp(-0.89/C) m²/s。体积热容固定为 rho cp；不显式加入蒸发潜热、辐射、接触传热和水分携带的焓。不计收缩及干物质损失。把附件烘房水分浓度直接作为有效平衡含水率 Ce，使用有限传质阻力边界。空气湿度与药材干基含水率的物理分母不同，此等同是缺少吸附等温关系时的闭合约定，并非已经证明的真实平衡关系。

热模型为 rho cp T_t=(1/r)(r k T_r)_r，水分模型为 C_t=(1/r)(r D(C) C_r)_r。轴心采用零径向导数，表面采用 k T_r=h(Tinf-Ts) 及 -D(Cs) C_r=hm(Cs-Ce)。两场在这一版本下解耦。输入在附件相邻时间点之间作线性插值，全部计算只用 0—1800 s 内的数据，无外推。物理推导、题目原文对应关系和完整算法见 `model/模型与算法_审查版本.tex`；该文是计算前的审查版本，其“尚未运行”等措辞是历史状态，本记录给出本轮新增运行证据。

## 实际离散配置及算法实施调整

保留包含轴心及表面节点的有限体积法、算术平均界面扩散系数、后向欧拉和 Picard 迭代。节点 r_i=iR/N，控制体权重 w_i=(r右²-r左²)/2，共享界面的通量在两侧使用相反符号。所有输出位置恰好落在网格节点上，不进行空间插值。

为了应对启动段边界与均匀初值不相容，又避免全程使用最小步长，计算使用预先规定的分段时间网格。记基本步长为 b，各区间的实际步长如下。

| 时间区间 / s | 步长倍数 | 温度步长 / s | 含水率步长 / s |
|---|---:|---:|---:|
'''
for lo,hi,m in [(0,2,1),(2,8,4),(8,32,16),(32,128,64),(128,512,128),(512,1800,256)]:text+=f"| [{lo}, {hi}) | {m} | {T['base_dt']*m:.12g} | {C['base_dt']*m:.12g} |\n"
text+=f'''
这是时间网格安排的实施调整，未改变离散方程和物理模型；不是根据误差估计自动增步。时间加密将整套步长同时减半。所有端点均与整数秒输出及60秒输入折点对齐。发生非线性不收敛时仍可拒绝该步并缩步，但本轮正式候选运行拒绝步数均为零；实际时间序列据预设网格重建，逐段累计步数与运行记录一致，保存在 `verification/accepted_time_grid_T.csv.gz` 和 `accepted_time_grid_C.csv.gz`，不能把该重建用于发生拒绝步的运行。

温度取自 `{T['run']}`，N={T['N']}，共 {T['steps']:,} 步。含水率取自 `{C['run']}`，N={C['N']}，共 {C['steps']:,} 步。利用方程解耦分别选取分辨率，避免让每个场都承担另一场所需的极高分辨率。当前统一计算核心每次仍会同时计算两场，但合并输出只选取各自通过验收的场，另一场不能因存在于同一运行中就自动被视为最终结果。

每步 Picard 同时检查状态增量和从新状态重新计算 D 后的原非线性残差。实际使用 eps=1e-12(1+max|C|)，比审查文暂定容差更紧；以重新组装的正对角系数对原残差逐分量归一化。最大50次迭代，最小步长保护值1e-6 s，线性范数后向误差门槛1e-12。单次求解的墙钟预算600 s；故意构造的失败测试之外，所有实际附件运行均正常到达1800 s。编译选项为 `-O3 -std=c++17`，没有启用 fast-math。没有随机量。

## 完整输出精度验收

下表取全部 1800×21 个输出位置的最大绝对差，而非只取论文表格中的位置。每一方向的门槛均为4e-6，对应各自状态量单位。

{chr(10).join(lines)}

温度时间差最大处为1272 s轴心，空间差最大处为300 s表面；含水率时间差最大处为228 s表面，空间差最大处为第1秒表面。因此验收确实覆盖了初期难点。三层比较的观测时间阶分别约为 {v['comparisons']['T_time_final_T']['observed_order']:.4f}、{v['comparisons']['C_time_final_C']['observed_order']:.4f}，空间阶分别约为 {v['comparisons']['T_space_final_T']['observed_order']:.4f}、{v['comparisons']['C_space_final_C']['observed_order']:.4f}。温度空间阶在统一 s65536 时间网格上测得，最终在更细 s131072 时间网格上再次作空间比较。所有比较的具体配置、位置和原始数值见 `verification/checks.json`。

将含水率 Picard 容差从1e-12收紧至1e-13，完整输出最大变化为 {v['tightening']['max_difference']:.8e} kg/kg，小于1e-7门槛。两次结果的四位小数全部相同。

加密差是经验数值稳定性证据，不是严格连续解误差上界。虽然上述门槛均已满足，靠近舍入分界的数值仍会发生第四位小数变化。最终两方向比较中，温度有 {roundcounts['T']} 个不同位置、含水率有 {roundcounts['C']} 个不同位置出现末位变化；时间与空间各自计数分别为温度549/60、含水率191/2，重叠位置只计一次。完整清单保存在 `verification/rounding_disagreements.csv`，因此没有宣称每个输出的第四位小数都已被唯一确定。Excel如实舍入实际细网格值，不通过截断或手工调整隐藏这些差异。

## 独立校验与收支诊断

已复现用户报告的粗网格差异。N=200、步长0.5→0.25 s的最大温度差为 {v['comparisons']['review_time_T']['max_difference']:.8e} °C，含水率差为 {v['comparisons']['review_time_C']['max_difference']:.8e} kg/kg；N=200→400、步长0.25 s的对应差为 {v['comparisons']['review_space_T']['max_difference']:.8e} °C 和 {v['comparisons']['review_space_C']['max_difference']:.8e} kg/kg。原配置未达到要求，本轮没有将它作为最终结果。

恒定初值与同值外界的平衡测试中，温度最大偏离 {v['equilibrium_max_error_T']:.3e} °C，含水率最大偏离 {v['equilibrium_max_error_C']:.3e} kg/kg。贝塞尔解析特例把扩散系数固定为5e-9，以 Robin 边界对应的 J0 特征函数作为精确解；非线性制造解取 C*=1+b+b(r/R)²，b=0.1 exp(-t/100)，由显式微分计算源项及与之相容的边界输入。这些测试不把主程序数值解当作参照解。

`src/verify.py` 使用贝塞尔幂级数评估解析参照，与 C++ 的系统贝塞尔函数实现不同；核查整数时刻的21个输出位置。C++另记录这些时刻全部内部节点的解析误差。制造源项为 f=-b(1+x²)/100-4b[D+b x² D·0.89/C²]/R²，x=r/R，控制体内用三点Gauss积分。测试步长均为1/4096 s、终点10 s；N=80、160、320逐次加倍。

| 测试 | N=80 最大误差 | N=160 最大误差 | N=320 最大误差 |
|---|---:|---:|---:|
'''
for mode,field,label in [('bessel','T','贝塞尔温度 / °C'),('bessel','C','贝塞尔含水率 / (kg/kg)'),('mms','C','非线性制造解 / (kg/kg)')]:
 rows=[r for r in v['analytical_cases'] if r['mode']==mode];text+='| '+label+' | '+' | '.join(f"{r['all_nodes_integer_times_error_'+field]:.8e}" for r in rows)+' |\n'
u=v['underiteration'];text+=f'''
单次 Picard 反例使用N=200、初始步长0.25 s，仅以旧含水率冻结 D 一次。独立 NumPy 稠密线性求解得到表面候选含水率 {u['surface_candidate']:.12f}，整体水分收支残差为 {u['single_frozen_solve_water_balance']:.3e}，但对新状态重新组装的原非线性残差为 {u['scaled_original_nonlinear_residual']:.8e}，约为稿件容差的 {u['ratio_to_paper_tolerance']:.3f} 倍。计算核心的拒绝测试返回退出码3、原因 `nonlinear_rejected`，接受步数为0。此测试是预期失败，不能与正常求解失败混淆；其统计文件未接受步的 min/max 初始化哨兵不具有物理含义。独立稠密解与C++拒绝测试的残差相符，不能用整体收支替代非线性检查。

最终所选温度运行的最大线性后向误差为 {T['stats']['max_linear_backward_error']:.3e}；所选含水率运行的最大原非线性缩放残差为 {C['stats']['max_scaled_nonlinear_residual']:.3e}，其相对接受门槛的最大比值为 {C['stats']['max_residual_ratio']:.3e}。每步均检查正性及由旧状态和当步边界值确定的范围，没有裁剪；初期约1e-12量级的界限偏离属于浮点舍入。

收支统计省略共同几何因子2πL。温度单步残差定义为 rho cp Σw(T新−T旧)−Δt R h(Tinf−Ts)，含水率定义为 Σw(C新−C旧)−Δt R hm(Ce−Cs)，后者未乘未知干物质密度。所选温度运行最大单步及累计有符号残差为 {T['stats']['max_heat_balance']:.3e}、{T['stats']['sum_heat_balance']:.3e}；所选水分运行对应值为 {C['stats']['max_water_balance']:.3e}、{C['stats']['sum_water_balance']:.3e}。它们只说明离散收支实现的一致性。

## 题目要求的论文表格

温度单位为 °C。

{tbl(1)}

干基含水率单位为 kg/kg。

{tbl(22)}

第1秒表面含水率为 {a[1,42]:.12f} kg/kg，是可用于手工比对早期结果的代表点。1800 s外界输入为41.513 °C及0.03307 kg/kg，此时模型内表面温度低于外界温度、表面含水率高于有效平衡值，分别对应向内输入热量及向外排出水分，边界通量方向与计算状态相容。

## 文件入口与复现

- `results/result1.xlsx` 为题目格式结果，`full_precision.csv` 为未舍入合并数据，两个 `paper_table_*.csv` 及 `paper_tables.tex` 为论文表格。
- `inputs/manifest.json` 记录题面、附件及模型文档原始路径和SHA-256；`verification/input_checks.json` 已逐值核对附件提取结果。
- `results/selection.json` 记录两个工作表各自来源、完整配置、原始输出校验值和最终诊断；`runs/*/manifest.json` 保留实际命令、软件平台、源代码/可执行文件校验值及起止时刻。
- `verification/checks.json` 是完整收敛和解析校验结果；`rounding_disagreements.csv` 是全部四位小数差异；`workbook_checks.json` 逐个验证75,600个导出值，Excel局部渲染图位于同目录。
- `src/solver.cpp` 是计算核心；`src/run_case.py` 创建不可覆盖的单次运行目录；`src/reproduce.sh` 给出本环境复现入口；`src/verify.py`、`prepare_results.py`、`build_workbook.mjs` 和 `check_workbook.py` 分别完成独立核验、结果抽取、工作簿导出及导出复核。

数值模型采用状态为候选，数值实现已通过本轮列出的解析特例、制造解、全范围加密及残差检查；没有实测药材内部状态可用于检验上述物理闭合假设。模型误差、经验参数误差和输入插值误差未被网格加密消除，也未计算参数不确定性区间。后续若修改含水率边界解释、加入潜热或收缩，需要建立新版本重新计算。

当前分支为 `q1/solve-m01-20260911`。文件为本地未提交成果，基准HEAD仅用于定位运行环境，不冒充本次源代码提交；实际源代码快照与哈希已保留。未提交、推送、合并或修改团队正式采用状态。
'''
(p/'README.md').write_text(text)
# Reusable TeX table fragment, using the same rounded raw values.
out='% Generated from results/full_precision.csv; requires booktabs.\n'
for col,caption in [(1,'30分钟内药材的温度（摄氏度）'),(22,'30分钟内药材的干基含水率（kg/kg）')]:
 out+='\\begin{table}[htbp]\n\\centering\n\\caption{'+caption+'}\n\\begin{tabular}{rrrrrr}\n\\toprule\n时间/s & 0 cm & 0.5 cm & 1 cm & 1.5 cm & 2 cm \\\\\n\\midrule\n'
 for t in [100,300,600,900,1200,1500,1800]:out+=str(t)+' & '+' & '.join(f'{a[t,col+j]:.4f}' for j in [0,5,10,15,20])+' \\\\\n'
 out+='\\bottomrule\n\\end{tabular}\n\\end{table}\n\n'
(p/'results/paper_tables.tex').write_text(out)
print('Report and TeX table fragments written.')
