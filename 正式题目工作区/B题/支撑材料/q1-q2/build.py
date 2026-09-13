"""Build the portable C++17 numerical kernel using CXX, clang++ or g++."""
from pathlib import Path
import os,shlex,shutil,subprocess
ROOT=Path(__file__).resolve().parent

def build(force=False):
    binary=ROOT/'build'/('q2_solver.exe' if os.name=='nt' else 'q2_solver')
    sources=[ROOT/'q2/solver.cpp',ROOT/'q2/geometry.hpp']
    if not force and binary.exists() and binary.stat().st_mtime>=max(p.stat().st_mtime for p in sources):
        return binary
    compiler=shlex.split(os.environ.get('CXX',''))
    if not compiler:
        found=shutil.which('clang++') or shutil.which('g++')
        if not found:raise RuntimeError('需要支持 C++17 的 clang++ 或 g++，也可通过 CXX 指定编译器。')
        compiler=[found]
    binary.parent.mkdir(exist_ok=True)
    temporary=binary.with_suffix('.tmp.exe' if os.name=='nt' else '.tmp')
    subprocess.run(compiler+['-std=c++17','-O3',str(sources[0]),'-o',str(temporary)],check=True)
    temporary.replace(binary)
    return binary

if __name__=='__main__':print(build(force=True))
