"""Replay saved actions with scalar angle physics; build result tables from JSON."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import numpy as np
from scipy.stats import t as student_t
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union

MODEL=Path(__file__).resolve().parents[1]
FINAL=['R006-final-v11','R007-final-outward','R008-final-tangent','R009-final-cluster']


def verify(data,record):
    sources={s['channel']:s for s in data['sources']}
    position=(0.,0.);channel=1;clock=0.;cleared=set();negative=set();failed=0
    successful=set();count=0;covers=0
    for a in record['actions']:
        q=a['point'];c=a['channel'];s=sources.get(c)
        move=math.sqrt(sum((x-y)**2 for x,y in zip(q,position)))/5
        position=q;extra=0.
        if a['kind']=='measure':
            extra=5+int(c!=channel);channel=c
            heard=False;distance=math.inf
            if s and c not in cleared:
                dx=q[0]-s['position'][0];dy=q[1]-s['position'][1]
                distance=math.sqrt(dx*dx+dy*dy)
                angle=math.degrees(math.atan2(dy,dx))%360
                difference=0 if s['direction_deg'] is None else (angle-s['direction_deg']+180)%360-180
                heard=distance<=s['radius_m']+1e-9 and abs(difference)<=90+1e-8
            response=a['response'];kind=response['measure_result']
            expected='no_signal' if not heard else ('near' if distance<=5+1e-9 else 'direction')
            assert kind==expected,(data['seed'],a,expected)
            if kind=='direction':
                truth=math.degrees(math.atan2(s['position'][1]-q[1],s['position'][0]-q[0]))%360
                error=abs((response['svd_deg']-truth+180)%360-180)
                assert error<=1.0051+1e-8,error
            if kind=='no_signal':negative.add((c,tuple(q)))
        else:
            distance=math.dist(q,s['position']) if s else math.inf
            ok=bool(s and c not in cleared and distance<=20+1e-9)
            assert ok==a['success']
            extra=5 if ok else 3
            if ok:cleared.add(c);successful.add((c,tuple(q)))
            else:failed+=1
        clock+=move+extra
        assert abs(clock-a['virtual_time_s'])<=1e-6
        assert abs(move+extra-a['delta_s'])<=1e-6
        count+=1
    result=record['result'];cert=result['completion']
    assert cleared==set(sources) and result['all_cleared'] and result['error'] is None
    assert abs(clock-result['virtual_time_s'])<=1e-6 and failed==result['failed_optical_attempts']
    assert cert['complete'] and not cert['observed_but_uncleared']
    if len(cleared)!=16:
        assert cleared | set(cert['excluded_channels'])==set(range(1,21))
    for c in cert['excluded_channels']:
        ids=set(cert['negative_vertex_indices'][str(c)])
        for tri in cert['triangles']:assert set(tri)<=ids
        for i in ids:assert (c,tuple(cert['mesh_points'][i])) in negative
        assert c not in sources
    for event in record['events']:
        c=event.get('channel')
        if event['kind']=='region':
            assert Polygon(event['vertices']).distance(Point(sources[c]['position']))<1e-5
        if event['kind']=='clear_certificate':
            assert event['worst_distance_m']<=19.500001
            assert math.dist(event['point'],sources[c]['position'])<=event['worst_distance_m']+1e-5
            assert (c,tuple(event['point'])) in successful
        if event['kind']=='optical_cover':
            covers+=1
            disks=unary_union([Point(q).buffer(19.49,quad_segs=32) for q in event['points']])
            assert Polygon(event['vertices']).difference(disks).area<1e-5
    return dict(actions=count,optical_covers=covers,failed_optical_attempts=failed)


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    summaries={};audit=dict(executions=0,actions=0,optical_covers=0,failed_optical_attempts=0)
    hashes={}
    for name in FINAL:
        folder=MODEL/'runs'/name
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        assert 'completed_at' in manifest
        for f,h in manifest['sources_sha256'].items():
            assert hashlib.sha256((folder/'source_snapshot'/f).read_bytes()).hexdigest()==h
            current=MODEL/'src'/f
            if current.exists():assert hashlib.sha256(current.read_bytes()).hexdigest()==h
        hashes[name]=hashlib.sha256((folder/'results.json').read_bytes()).hexdigest()
        rows=json.loads((folder/'results.json').read_text(encoding='utf-8'))
        summaries[name]={}
        for row in rows:
            seed,policy=row['seed'],row['policy']
            data=json.loads((folder/f'fixture-{seed}.json').read_text(encoding='utf-8'))
            record=json.loads((folder/f'{seed}-{policy}.json').read_text(encoding='utf-8'))
            checked=verify(data,record);audit['executions']+=1
            for k,v in checked.items():audit[k]+=v
        for policy in ['mesh_chase_baseline','directional_v1']:
            subset=[r for r in rows if r['policy']==policy]
            summaries[name][policy]=dict(cases=len(subset),all_clear=sum(r['all_cleared'] for r in subset),
                mean_s=float(np.mean([r['average_s'] for r in subset])),
                median_s=float(np.median([r['average_s'] for r in subset])),
                mean_route_m=float(np.mean([r['distance_m'] for r in subset])),
                mean_measures=float(np.mean([r['measures'] for r in subset])),
                mean_failed_optical=float(np.mean([r['failed_optical_attempts'] for r in subset])),
                mean_fallbacks=float(np.mean([r['completion']['optical_fallbacks'] for r in subset])),
                mean_tail_s=float(np.mean([r['tail_s'] for r in subset])),
                max_wall_s=max(r['wall_s'] for r in subset))
    final=json.loads((MODEL/'runs'/FINAL[0]/'results.json').read_text(encoding='utf-8'))
    base={r['seed']:r for r in final if r['policy']=='mesh_chase_baseline'}
    new={r['seed']:r for r in final if r['policy']=='directional_v1'}
    differences=np.array([base[k]['average_s']-new[k]['average_s'] for k in sorted(base)])
    half=float(student_t.ppf(.975,len(differences)-1)*np.std(differences,ddof=1)/math.sqrt(len(differences)))
    paired=dict(mean_saved_s=float(differences.mean()),ci95=[float(differences.mean()-half),float(differences.mean()+half)],
                better=int(np.sum(differences>1e-7)),worse=int(np.sum(differences<-1e-7)),
                seed_order=sorted(base),saved_s=differences.tolist())
    result=dict(groups=summaries,paired=paired,audit=audit,result_sha256=hashes)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 第四问初版策略与本地验证结果','',
      '当前候选为P4-M01/A01 v1.1：三角网定向覆盖、可见性假设选点、联合路线及光学区域后备。它侧重先建立可复核的全清逻辑，尚无官方演练成绩，也未证明时间最优。',
      '', '## 冻结后的同场比较','',
      '主审计25000–25039共40场，位置在圆内均匀、接收半径在1000–1500内均匀，朝向均匀；混合类型随机生成并确保至少一个全向、一个定向。固定空间误差为正弦函数，不假定同点重复测量独立。',
      '', '| 批次 | 场数 | 简单基线秒/点 | 初版秒/点 | 两版全清 |', '|---|---:|---:|---:|---|']
    titles=['随机混合主审计','边界朝外/R=1000/+1°','边界切向/R=1000/−1°','近源聚集/R=1000/棋盘±1°']
    for name,title in zip(FINAL,titles):
        b=summaries[name]['mesh_chase_baseline'];v=summaries[name]['directional_v1']
        lines.append(f'| {title} | {v["cases"]} | {b["mean_s"]:.2f} | {v["mean_s"]:.2f} | {b["all_clear"]}/{b["cases"]}，{v["all_clear"]}/{v["cases"]} |')
    b=summaries[FINAL[0]]['mesh_chase_baseline'];v=summaries[FINAL[0]]['directional_v1']
    lines += ['',f'主审计同场平均节省{paired["mean_saved_s"]:.2f}秒/点（{100*paired["mean_saved_s"]/b["mean_s"]:.2f}%）；近似配对95% t区间[{paired["ci95"][0]:.2f},{paired["ci95"][1]:.2f}]，{paired["better"]}场改善、{paired["worse"]}场退化。区间仅描述这类合成分布，不代表官方总体。',
      '',f'初版每场平均路程{v["mean_route_m"]:.2f}m、测量{v["mean_measures"]:.2f}次、光学失败尝试{v["mean_failed_optical"]:.2f}次、后备定位{v["mean_fallbacks"]:.2f}次、最后清除后的收尾{v["mean_tail_s"]:.2f}s；单场最大本地计算墙钟{v["max_wall_s"]:.2f}s。光学失败尝试属于后备搜索的真实费用，全部计入结果。',
      '', '## 正确性和证据范围','',
      f'独立逐动作回放核对了{audit["executions"]}次策略执行、{audit["actions"]}个动作：使用标量角度判定接收、重算移动/检测/换频/清除成本、检查示向度误差界、真值包含、安全清除上界及每个排除频道的真实负观测。还用19.49m内接圆盘多边形独立核验了{audit["optical_covers"]}个实际光学后备覆盖。全部通过。',
      '', 'V002连续几何验证包括三角网覆盖整个圆域的外接多边形、最大三角形边长990m、360次正观测保留真值、120次背向无信号不错误删除位置、4组长条定位域光学覆盖。V001的几何库拼接精度冲突及处理保留，未隐藏。',
      '', '## 如何结合前问经验','',
      '继承Q1有界测角区域与最小包围圆、M03最近保证清除点和已验证的串行HTTP客户端。Q2的全向接收保证、Q3无信号排除1000m圆盘和原全向搜索完成条件均不直接继承。有限朝向样本只用于选择测量点，不参与硬清除/停止证明。',
      '', 'Q3 v5显示额外测量会抵消移动收益，所以初版没有在每个路过点自动补测所有已知频道。当前路线仍以目标中心近似服务位置；两个因素同时改变，不能把全部收益单独归因于朝向模型。',
      '', '## 版本和限制','',
      'R001为两场小样例。R002–R005保留第一次冻结实现的结果；随后发现“已发现16个不同频道”即可停止未知频道搜索，加入此逻辑形成v1.1。最终数据全部使用新的25000起种子R006–R009，未用旧结果冒充新实现成绩。网格负观测登记改为坐标完全相同，避免角度边界证书被近似位置污染。',
      '', '搜索网格固定且偏保守，31个站点中18个位于场外，缺少利用任意历史检测位置缩减覆盖任务的能力，导致时间明显较高。朝向/半径假设有限、评分是启发式，失去信号时也未充分利用联合可行集。光学后备可能产生多次失败尝试；现实HTTP延迟、20分钟预算及官方分布尚未验证。',
      '', '下一步应优先做自适应方向覆盖和已有观测复用，其次做失联后的联合位置—朝向推断及服务路径；不能只比较第三问和第四问不同分布的均值。当前仅为可演练初版，不是200秒级或最终竞赛方案。',
      '', '完整策略推导见../../formulations/v01.md，运行说明见../../src/使用说明.md。本报告及所有表格由audit_and_report.py从原始JSON生成；代码与运行记录已保存本地，尚未提交推送，也未登记团队采用。']
    (out/'第四问初版与验证.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    shutil.copy2(Path(__file__),out/'audit_and_report.py')
    print(json.dumps(dict(main=summaries[FINAL[0]],paired={k:v for k,v in paired.items() if k not in ['seed_order','saved_s']},audit=audit),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
