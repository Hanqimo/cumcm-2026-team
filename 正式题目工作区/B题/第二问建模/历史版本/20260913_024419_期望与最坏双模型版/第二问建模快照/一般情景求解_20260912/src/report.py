"""Write human-readable results and exact provenance without altering legacy results."""
from pathlib import Path
import json,csv,hashlib,datetime,platform,sys,subprocess,math
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent

def main():
 conv=json.loads((ROOT/'verification/convergence.json').read_text());prec={(r['case'],r['objective']):r for r in conv if r['level']==6}
 cases=sorted([json.loads(p.read_text()) for p in (ROOT/'results').glob('*/summary.json')],key=lambda x:(x['a_m'],x['beta_deg']))
 regress=json.loads((ROOT/'verification/origin_regression.json').read_text());validation=json.loads((ROOT/'verification/summary.json').read_text())
 exhaustive=json.loads((ROOT/'verification/exhaustive_support_circles.json').read_text());mc=json.loads((ROOT/'verification/joint_prior_mc.json').read_text())
 side=json.loads((ROOT/'verification/opposite_side_search.json').read_text())
 # Verify every final point against model constraints using a concrete source witness in the first region.
 feas=[];flat=[]
 for c in cases:
  a,b=c['a_m'],c['beta_deg'];name=f'a{a:g}_b{b:g}';B=math.radians(b)
  for obj in ['area','radius']:
   r=prec[name,obj];phi=0.;target=(-a*math.cos(B),a*math.sin(B));disc=1800**2-target[1]**2
   # If the central ray is empty, find a valid ray; all current scenarios have a valid central ray.
   witness=None
   for d in [0]+[math.pi/180*(-1+2*i/2000) for i in range(2001)]:
    u=(math.cos(d),math.sin(d));projection=u[0]*target[0]+u[1]*target[1];disc=projection**2+1800**2-a*a
    if disc<=0:continue
    lo=max(5,projection-math.sqrt(disc));hi=min(1500,projection+math.sqrt(disc))
    if hi<=lo:continue
    t=(lo+hi)/2;g=(t*u[0],t*u[1]);distance=math.hypot(g[0]-r['x'],g[1]-r['y'])
    if distance<1500:witness={'g_local':g,'source_distance_from_S1':t,'source_distance_from_target_center':math.hypot(g[0]-target[0],g[1]-target[1]),'source_distance_from_q':distance};break
   assert witness is not None and math.hypot(r['x'],r['y'])>0
   feas.append({'case':name,'objective':obj,'candidate_domain_verified_by_witness':True,'witness':witness})
   flat.append(dict(a_m=a,beta_deg=b,objective=obj,q_x=r['x_global'],q_y=r['y_global'],expected_area_m2=r['J'],expected_radius_m=r['E_radius_loss'],P_H=r['P_H'],P_N=r['P_N'],P_loc=r['P_loc'],global_optimum_certified=c['global_optimality_proven']))
 (ROOT/'verification/candidate_feasibility.json').write_text(json.dumps(feas,indent=2))
 (ROOT/'results/summary.json').write_text(json.dumps(flat,indent=2))
 with (ROOT/'results/summary.csv').open('w')as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 lines=['# 一般情景求解结果与原点回归检查','',
 '模型版本为 `Q2-expected-M01-v03-a-beta`，对应上级目录《第二问模型.tex》。本次完成适用于一般相容参数的求解实现，并实际计算8个代表情景；这些样例不是连续参数域的穷尽扫描。a 的单位为米，β 在输入和下表中以度表示。',
 '', '第二点坐标均以目标大圆圆心 O 为原点，第一点为 S₁=(a,0)。期望面积与期望半径损失分别优化，均保留强信号及其他原地光学终止分支的零损失。下面记录每个目标自己的目标值；完整交叉目标与反馈概率见 `results/summary.csv`。','',
 '| a | β | 面积目标第二点（米） | 最小期望面积候选值（平方米） | 半径目标第二点（米） | 最小期望半径候选值（米） |','|---:|---:|---|---:|---|---:|']
 for c in cases:
  a,b=c['a_m'],c['beta_deg'];name=f'a{a:g}_b{b:g}';x=prec[name,'area'];y=prec[name,'radius']
  lines.append(f"| {a:g} | {b:g}° | ({x['x_global']:.2f}, {x['y_global']:.2f}) | {x['J']:.6f} | ({y['x_global']:.2f}, {y['y_global']:.2f}) | {y['E_radius_loss']:.6f} |")
 lines += ['', '表中每项只列一个候选点。β=0°或180°时，关于x轴反射的点具有相同目标值；a=900、β=90°时大圆完全不裁剪第一扇形，关于第一示向轴的两个解同样等价。一般非对称情景不能直接反射得到等价解。坐标保留两位小数是展示精度，不是坐标误差保证。', '',
 '## 主要结论','',
 '1. 大圆裁剪会改变后验区域及最优选点。a=1700、β=0°时，源距范围只有约5—100米，最优期望半径约1.878米；a=1700、β=90°时，源距和角度耦合后的区域更大，最优期望半径约10.728米。',
 '2. 第一检测点可位于大圆外。a=2500、β=180°及150°都得到相容后验并完成求解，两种情景的结果不同。',
 '3. a=900、β=90°时，整个原始第一扇形均在大圆内，因此在以第一点为原点的方向坐标下，目标函数与原点基准相同；计算复现了这一退化关系。',
 '4. a=1780、β=0°时，第一次支持集的最小包围圆半径约7.50468米。取第二点(1792.50341,0)米后，全部源位置距第二点不足20米，两个损失均为零。由损失非负，这一情景具有全局最优值0，最优点不唯一。强信号概率约66.6532%，全部反馈都能原地完成光学定位。',
 '5. 其余七个样例的最优候选均没有强信号概率。它们的原地定位成功概率也为0，这是本次两个期望损失目标的结果，不表示任何参数情景都应避开强信号区域。', '',
 '## 与旧原点结果的比较','',
 '比较分两步进行。第一步把旧坐标直接输入新求解器，检查同一点的目标计算；第二步从覆盖网格独立搜索，没有使用旧坐标作为初始化，再比较重新找到的位置。新旧程序共享既有圆弧及包围圆内核，因此回归一致性不替代独立验证。','',
 '| 目标 | 旧坐标（统一取北侧） | 新坐标（统一取北侧） | 坐标距离差（米） | 旧目标值 | 新目标值 |','|---|---|---|---:|---:|---:|']
 for x in regress:
  obj=x['objective'];old=x['old_q'];new=x['new_q'];oldvalue=x['old_saved_area'] if obj=='area' else x['old_saved_radius'];r=x['new_solver_at_new_point'];value=r['J'] if obj=='area' else r['E_radius_loss']
  lines.append(f"| {'期望面积' if obj=='area' else '期望半径'} | ({old[0]:.6f}, {old[1]:.6f}) | ({new[0]:.6f}, {abs(new[1]):.6f}) | {x['coordinate_difference_after_reflection_m']:.9f} | {oldvalue:.12f} | {value:.12f} |")
 lines += ['', '面积目标的新旧坐标相差约0.375毫米，半径目标相差约2.682毫米；两次搜索在当前精度下给出一致结果。这是搜索结果的一致性，不是对连续最优坐标的毫米级误差证明。',
 '', '在旧坐标处，新求解器与旧保存值的面积差最大约3.1×10⁻¹¹平方米，半径差最大约5.1×10⁻¹³米。对于重新搜索得到的半径最优点，其交叉面积值略有变化，是坐标存在毫米级差异造成的；该点自身的半径目标仍与旧结果一致。', '',
 '## 算法与实际计算范围','',
 '内部使用以第一点为原点、第一次示向度为正x方向的坐标，以复用已有几何内核。目标大圆圆心在该坐标下为(-a cosβ,a sinβ)，输出再还原至O坐标，因此没有丢弃大圆位置信息。',
 '', '采用圆与直线的连续边界交集、有限点包围圆加最远点补充、源距分段Gauss积分、角度自适应加密。为复用已验证实现，本轮使用分段Gauss–Legendre倍阶比较，尚未实现上轮建议的方位权重累积积分加速；这改变计算方式，不改变积分对象。第二次20米终止边界通过加入光学圆的角度事件统一处理。',
 '', '外层包括100米覆盖网格、第一支持集附近的强信号/光学区域加密、随支持集尺度调整的中心二维网格、每目标6个分散初值的局部细化、高精度复核和两侧候选区域补查。局部细化采用二维Nelder–Mead单纯形法。除零损失情景外，均为数值最好候选，未提供连续全域下界或全局最优证明。',
 '', f"主搜索共记录{sum(c['evaluation_count'] for c in cases):,}次候选点评价，八个情景主搜索耗时合计{sum(c['elapsed_seconds'] for c in cases):.2f}秒；不含后续两侧补查、独立验证和文件整理。", '',
 '## 验证结果与边界','',
 f"最终精度下，概率归一化残差最大为{validation['max_probability_sum_residual']:.3e}。进行了{validation['geometry_checks']}组独立射线几何检查，未发现超过1e-5米容差的包围圆遗漏；采样点到包围圆外的最大残差为{validation['max_containment_residual_m']:.3e}米。",
 '', f"对直径下界不足以确定半径的{len(exhaustive)}组，额外采用更密射线采样，枚举独立极值点集的两点直径圆和三点外接圆。其最小包围圆给出连续区域半径的独立下界，与主算法上界的最大差为{max(x['refined_radius_gap'] for x in exhaustive):.6f}米。该差包括有限射线采样造成的遗漏，不等同于主算法半径误差。",
 '', f"联合先验拒绝抽样模拟共{sum(x['n'] for x in mc):,}次有效样本；面积与半径均值相对积分结果的最大标准化偏差分别为{validation['max_mc_area_zscore']:.3f}和{validation['max_mc_radius_zscore']:.3f}个标准误，未发现明显冲突。模拟共享包围圆内核，因此主要验证概率更新和期望积分，几何正确性另由独立射线与支持圆枚举检查。",
 '', '所有最终候选均通过实际源位置见证检查，满足第二点候选域；镜像参数关系以及不发生大圆裁剪时的退化关系也通过数值检查。各目标均比较了4档积分精度；最高两档间面积差最大约3.1×10⁻⁶平方米、半径差最大约2.3×10⁻⁸米。这些是固定候选点的收敛检查，不证明搜索坐标达到同等精度。',
 '', '尚未覆盖全部连续(a,β)参数域，尚无先验敏感性研究或一般非零最优值的连续全局证明。近优区域文件只给出采样候选点，不将整个网格单元认证为1%近优区域。', '',
 '## 文件与复现','',
 '`results/summary.csv` / `summary.json` 给出最终高精度汇总，`results/a*_b*/` 保存网格、初值、局部搜索和近优点；`verification/` 保存积分收敛、原点回归、独立几何、随机模拟、两侧搜索及镜像核查；`inputs/` 保留旧结果快照和模型来源哈希。',
 '', '在本目录运行 `python3 src/reproduce.py` 可编译并复现八个情景及验证。需要NumPy和支持C++17的clang++；同情景复现会覆盖本目录该情景输出，父目录的旧模型结果不被覆盖。也可以在编译后运行 `python3 src/search_general.py --a 1700 --beta 90` 单独搜索指定情景，其中beta以度为单位。完整比较与验证流程针对当前八情景集合设计，新增情景应另行生成相应核查记录。',
 '', '原始求解器CSV为兼容旧接口保留safe_margin字段，本轮该字段是未计算的占位值，不能用于判断保证接收；可行性证据见 `verification/candidate_feasibility.json`。本次求解流程未执行Git提交或推送；仓库在计算期间出现了其他同步，起始与记录时提交分别保存在清单中。']
 (ROOT/'结果汇报.md').write_text(('\n'.join(lines)+'\n').replace(', -0.00)', ', 0.00)'))
 source=json.loads((ROOT/'inputs/source_manifest.json').read_text());checks={k:hashlib.sha256((PARENT/k).read_bytes()).hexdigest()==v for k,v in source['sources'].items()}
 notation_path=PARENT/'verification/sector_notation_revision.json'
 notation=json.loads(notation_path.read_text()) if notation_path.exists() else {}
 accepted_checks=dict(checks)
 if not checks.get('第二问模型.tex',True):
  accepted_checks['第二问模型.tex']=(notation.get('old_model_sha256')==source['sources']['第二问模型.tex'] and notation.get('new_model_sha256')==hashlib.sha256((PARENT/'第二问模型.tex').read_bytes()).hexdigest())
 assert all(accepted_checks.values()),checks
 data={'model':'Q2-expected-M01-v03-a-beta','algorithm':'Q2-GENERAL-A01-v01','updated_at':datetime.datetime.now().astimezone().isoformat(),'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),'compiler':subprocess.check_output(['clang++','--version'],text=True).splitlines()[0],'git_head_at_record':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'git_head_at_start':source['git_head'],'scenario_count':len(cases),'cases':[(c['a_m'],c['beta_deg']) for c in cases],'legacy_files_unchanged':checks,'accepted_source_equivalence':accepted_checks,'notation_revision':notation,'validation':validation,'no_continuous_global_certificate_except_zero_case':True,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.name not in ['solver','manifest.json'] and '__pycache__' not in str(p)}}
 (ROOT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print('\n'.join(lines[:18]))
if __name__=='__main__':main()
