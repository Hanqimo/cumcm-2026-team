from pathlib import Path
import json, math, csv, hashlib, platform, sys, subprocess
ROOT=Path(__file__).resolve().parents[1]
def table(rows):
    return '| 时间/h | 0 cm | 0.5 cm | 1 cm | 1.5 cm | 2 cm |\n|---:|---:|---:|---:|---:|---:|\n'+'\n'.join('| '+' | '.join([f'{r[0]:.1f}']+[f'{v:.4f}' for v in r[1:]])+' |' for r in rows)
def main():
    s=json.loads((ROOT/'results/summary.json').read_text());c=json.loads((ROOT/'verification/checks.json').read_text());st=s['stats'];com=c['comparisons'];bd=c['independent_BDF']['richardson_extrapolation']
    checks='| 检查 | 温度最大差/℃ | 含水率最大差/(kg/kg) |\n|---|---:|---:|\n'
    for key,label in [('space','空间N=6400→12800'),('time','基本步长1/512→1/1024 s'),('tolerance','迭代容差1e-12→5e-13')]:checks+=f"| {label} | {com[key]['T']['max_difference']:.9g} | {com[key]['C']['max_difference']:.9g} |\n"
    report=f'''# A题问题2计算报告

模型 Q2-M01-v01；算法 A01（径向有限体积、隐式中点与后向欧拉启动、双场Picard）；数据 D01。计算范围0—10800 s。本次按用户授权采用不计潜热方案，模型和算法说明见[模型与求解算法](model/模型与求解算法.md)。本目录为本地研究成果，不代表团队已完成正式采用或发布。

## 主要结果

3小时后，中心温度为{ s['table3'][-1][1]:.4f}℃，表面温度为{s['table3'][-1][-1]:.4f}℃，中心与表面温差约{s['table3'][-1][-1]-s['table3'][-1][1]:.4f}℃。中心干基含水率为{s['table4'][-1][1]:.4f} kg/kg，表面为{s['table4'][-1][-1]:.4f} kg/kg。温度已接近环境，但水分仍存在明显径向梯度。

按圆柱控制体权重计算，3小时体积平均温度为{s['mean_T_3h']:.6f}℃，平均干基含水率为{s['mean_C_3h']:.6f} kg/kg。在固定且均匀干物质体积密度假设下，约排出了初始水量的{100*s['fraction_of_initial_water_removed']:.4f}%。没有将题给有效密度擅自换算为绝对失水克数。

### 表3：3小时内药材温度（℃）

{table(s['table3'])}

### 表4：3小时内药材干基含水率（kg水/kg干物质）

{table(s['table4'])}

## 算法执行与收敛

最终数据来源为 `{s['final_run']}`，两个状态场使用同一空间和时间网格，N={st['N']}，径向步长为{.02/st['N']:.10g} m。基本时间步长1/1024 s，启动后按分段倍数增大，最终阶段为0.25 s。总计{st['steps']}个接受步，拒绝步数{st['rejected']}，最多{st['max_picard']}次Picard迭代。实际数据未触发状态范围保护；微小浮点越界只在约1e-11量级。

下表比较全部10800×21个输出点，均包括第1秒表面；空间比较保持时间网格一致，时间比较保持空间网格一致。

{checks}

预先设定的两种加密门槛均为4e-6，容差收紧门槛为1e-7。完整检验通过。初次收紧至1e-13时第129秒前后出现一次拒绝步，改变了后续时间网格，最大温差2.5103e-7℃超过纯容差检查门槛，因此不把该次运行冒充同网格容差验证。随后使用5e-13，在相同时间网格上完成上述对比；更严格的混合变动结果仍保留。空间含水率最大差发生在{com['space']['C']['time_s']} s、{com['space']['C']['r_cm']:.1f} cm处，符合初始不相容边界最难分辨的特点。空间温度最大差发生在{com['space']['T']['time_s']} s、{com['space']['T']['r_cm']:.1f} cm处。

加密差是经验数值证据，不是连续解误差的严格上界。所有加密和容差比较合并去重后，温度有{c['rounding_unique_positions']['T']}个、含水率有{c['rounding_unique_positions']['C']}个位置的四位小数末位发生变化。具体位置保存在[舍入差异清单](verification/rounding_disagreements.csv)。Excel显示四位小数但保留底层数值，CSV保留双精度，不以截断或手工调整掩盖末位变化。

## 独立验证与收支

均匀平衡测试的最大偏离为温度{c['analytic_checks']['equilibrium']['T']:.3g}℃、含水率{c['analytic_checks']['equilibrium']['C']:.3g}。常物性Bessel解析解及双场非线性制造解均随空间加密降低误差；解析参照由独立Python函数评估，制造源项还以五点数值微分的通量导数进行交叉核对，不由主离散算子构造参照。

实际数据另用单元中心有限体积、调和平均、表面半单元阻力和自适应BDF计算。N=400、800、1600的结果随加密趋近主解。N=1600在六个论文时刻的最大差为温度{c['independent_BDF']['1600']['paper_times_T']:.6g}℃、含水率{c['independent_BDF']['1600']['paper_times_C']:.6g} kg/kg。利用N=800和1600的经验二阶Richardson外推，在全部独立检查点的最大差为温度{bd['max_T']:.6g}℃、含水率{bd['max_C']:.6g} kg/kg。外推提供交叉支持，不是严格误差界；独立方法的有限网格早期表面误差及全部结果也已保留。

最终计算的最大原方程缩放残差为温度{st['residual_T']:.6g}℃、含水率{st['residual_C']:.6g} kg/kg，线性后向误差为{st['linear_backward_error']:.6g}。累计有效显热收支残差为{c['balance']['heat_J']:.6g} J，归一化水收支的相对残差为{c['balance']['water_relative']:.6g}；含水率平均量与累计边界排水的恒等式误差为{c['balance']['mean_moisture_identity_error']:.6g} kg/kg。热量检查对应B(C)T_t，不是d[B(C)T]/dt，也不替代完整热力学验证。

## 物理解释边界

潜热假设仍未解决。此处不计潜热是当前工作约定，而非已证实潜热很小。附录3的D依赖温度，所以将来改变潜热处理时温度和含水率都需重新计算。有效平衡含水率等同环境数值、沿用表面系数、忽略端面和收缩，以及变密度仅作为有效热物性参数的解释，也应随结果保留。

前三小时完全使用附件覆盖范围内的线性插值，没有调用50℃、0.05的长期外推。本次没有求解问题3，没有以中心或平均含水率替代“各处达标”的后续判据。

## 文件入口与复现

- [result2.xlsx](results/result2.xlsx)：温度和水分浓度两个工作表，各10800行×21个结果值，时间从1秒开始，显示四位小数。
- [完整双精度CSV](results/full_precision.csv)：含初始时刻，列T_0—T_20与C_0—C_20分别对应0—2 cm、间隔0.1 cm。
- [表3 CSV](results/表3_温度.csv)、[表4 CSV](results/表4_含水率.csv)：六个时刻、五个位置的论文表格，原始数值未预先舍入。
- [最终内部网格](results/final_internal_grid.csv)、[平均量及收支](results/diagnostics.csv)、[结果摘要](results/summary.json)。
- [验证汇总](verification/checks.json)、[验证方案](verification/plan.md)、[复现说明](复现说明.md)。

各次运行保存配置、输入和源码哈希、实际命令、源代码快照、完整输出和停止原因。R004与R005因内部计时预算终止，未纳入最终完整输出；未完成运行保留以供追溯。机器计时原始值有不一致，保留外层manifest与C++内部stats两份读数，不报告伪精确的统一耗时。本次未提交、推送或修改问题1结果。
'''
    (ROOT/'README.md').write_text(report)
    (ROOT/'state.md').write_text('''# 问题2当前研究状态

本轮任务为用户授权的算法设计、实际求解和结果保存。模型Q2-M01-v01，算法A01，数据D01。采用状态为当前工作方案；未修改团队正式采用入口。G0、G1、G2、G3完成；G4的计算实现和独立特例检查通过，物理闭合尚未获验证；G5已记录适用范围与下一步。

正式候选运行R006_N12800_s1024，结果见README及results/summary.json。前三小时已计算，不开始问题3。物理未决事项为潜热、环境湿度到材料平衡含水率的换算、变密度与固定几何的一致解释、端面及表面系数简化。

当前结果是在已列假设下的数值解，不是经实验验证的真实干燥预测。后续若改动这些机制，需要新模型版本及重新求解验证。仅本地保存，未提交、未推送。
''')
    (ROOT/'research-log.md').write_text('''# 本轮研究记录

先核对题面和附件及问题1两种潜热方案，在用户明确授权下采用无潜热变物性模型。初始试算N=400揭示早期表面空间误差；N=1600、3200进一步定位第1秒表面为水分误差主导点。均匀平衡、Bessel解析特例及非线性制造解通过，后续独立BDF结果显示不同离散路径的一致趋近。

过细时间配置R004、R005触及内部计时预算，保留中断记录。N=3200的步长比较表明最大步长1秒温度误差较大，0.5秒和0.25秒配置已明显降低差异，故选择N=12800、末段0.25秒的R006。分别进行同时间网格空间比较、同空间网格时间比较及容差收紧，最终完整输出通过预设门槛。

原运行环境缺少SciPy；首次尝试安装因网络沙箱无法解析地址失败，随后在临时目录完成安装，没有改动Bundled Python目录。独立分析环境配置见复现说明。分析器首次在容差运行未完成时读到了未写完CSV，未采纳该次分析，完成后重新执行所有分析断言。

最终结果及验证以checks.json、summary.json和各运行manifest为准，不把程序正常退出单独当作正确性证据。
''')
    inventory=[]
    for p in sorted((ROOT/'runs').glob('*/manifest.json')):
        m=json.loads(p.read_text());inventory.append({'run':p.parent.name,'config':m.get('config',{'N':m.get('N')}),'completed':m.get('returncode',0)==0,'manifest':str(p.relative_to(ROOT))})
    (ROOT/'verification/run_inventory.json').write_text(json.dumps(inventory,indent=2))
    print('Reports written',s['final_run'])
if __name__=='__main__':main()
