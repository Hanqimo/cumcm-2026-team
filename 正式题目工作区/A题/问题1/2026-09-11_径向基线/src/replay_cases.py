"""Replay retained cases sequentially; expected rejection must still reject."""
from pathlib import Path
import sys,json,subprocess
p=Path(__file__).resolve().parents[1]
for a in json.loads((p/'src/cases.json').read_text()):
 cmd=[sys.executable,str(p/'src/run_case.py'),a['name'],'--exe',sys.argv[1]]
 for field in ['n','dt','schedule','end','tol','mode','maxit','budget']:cmd.extend(['--'+field,str(a[field])])
 result=subprocess.run(cmd)
 expected=3 if a['mode']=='onepicard' else 0
 if result.returncode!=expected:raise RuntimeError(f"Case {a['name']}: code {result.returncode}, expected {expected}")
