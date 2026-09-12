"""Rebuild, solve, audit and validate the documented eight scenarios."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1]
subprocess.run(['clang++','-std=c++17','-O3',str(root/'src/solver.cpp'),'-o',str(root/'solver')],check=True)
for name in ['search_general.py','audit_search.py','validate_general.py','extra_checks.py','report.py']:
 subprocess.run([sys.executable,str(root/'src'/name)],cwd=root,check=True)
