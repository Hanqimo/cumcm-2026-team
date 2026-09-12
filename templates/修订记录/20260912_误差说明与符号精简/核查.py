"""检查接收半径消元的边界，以及从权重式到直接积分式的代数一致性。"""
from pathlib import Path
import hashlib
import json
import math
import random
import re

here = Path(__file__).resolve().parent
tex = here.parents[1] / '论文模版.tex'
s = tex.read_text()
old = (here / '论文模版_编译修复后.tex').read_text()

def part(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]

assert part(s, r'\section{问题一的模型建立与求解}', r'\section{问题二：第二检测点的两种优化模型}') == part(old, r'\section{问题一的模型建立与求解}', r'\section{问题二：第二检测点的两种优化模型}')
assert part(s, r'\section{符号说明}', r'\section{问题分析}') == part(old, r'\section{符号说明}', r'\section{问题分析}')
q2 = part(s, r'\section{问题二：第二检测点的两种优化模型}', r'\section{模型检验}')
for token in ('A_1', r'A_z', r'\mathcal F', 'M_z', r'p_{2,G}', r'\overline{A'):
    assert token not in q2

def w(d):
    return max(0.0, min(1.0, (1500-d)/500))

distances = [0, 5-1e-6, 5, 5+1e-6, 999, 1000, 1000+1e-6,
             1499, 1500, 1500+1e-6, 1600]
rng = random.Random(912)
pairs = [(x,y) for x in distances for y in distances]
pairs += [(rng.uniform(5.01,1499.99),rng.uniform(0,2000)) for _ in range(1000)]
checked = 0
max_error = 0.0
for d1,d2 in pairs:
    if not (5 < d1 <= 1500):
        continue
    # Independently eliminate the shared radius by checking a witness at its
    # smallest admissible value, rather than using the piecewise probability.
    lower = max(1000,d1)
    no_signal_exists = lower <= 1500 and lower < d2
    assert no_signal_exists == (d2 > max(1000,d1))
    normal_exists = 5 < d2 and max(1000,d1,d2) <= 1500
    assert normal_exists == (5 < d2 <= 1500)
    # Integrate uniform R directly by interval length and compare with weights.
    mass_h = (1500-lower)/500 if d2 <= 5 else 0.0
    mass_n = max(0,min(1500,d2)-lower)/500
    mass_b = max(0,1500-max(lower,d2))/500 if d2 > 5 else 0.0
    weight_h = w(d1) if d2 <= 5 else 0.0
    weight_n = w(d1)-w(max(d1,d2))
    weight_b = w(max(d1,d2)) if d2 > 5 else 0.0
    error = max(abs(a-b) for a,b in zip((mass_h,mass_n,mass_b),(weight_h,weight_n,weight_b)))
    max_error = max(max_error,error)
    assert error < 1e-12
    assert math.isclose(mass_h+mass_n+mass_b,w(d1),abs_tol=1e-12)
    checked += 1

labels = re.findall(r'\\label\{([^}]+)\}',s)
assert len(labels) == len(set(labels))
assert set(re.findall(r'\\(?:ref|eqref|cref)\{([^}]+)\}',s)) <= set(labels)
log = tex.with_suffix('.log').read_text()
assert not re.search(r'^!|Warning|Error|Missing character|Overfull|Underfull',log,re.M)
report = {'q1_unchanged': True, 'global_symbol_table_unchanged': True,
          'distance_cases_checked': checked, 'weight_max_difference': max_error,
          'strict_inequalities_preserved': True, 'references_resolve': True,
          'compile_warnings_or_errors': 0,
          'tex_sha256':hashlib.sha256(tex.read_bytes()).hexdigest()}
(here/'核查结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
