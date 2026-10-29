"""Compile only this project's own kernel with the host C compiler."""
from pathlib import Path
import shutil
import subprocess
import sys

if sys.platform not in ('darwin', 'linux'):
    raise SystemExit('Native demo build supports macOS/Linux only; Python backend remains available.')
root = Path(__file__).resolve().parents[1]
compiler = shutil.which('cc')
if not compiler:
    raise SystemExit('A host C compiler (cc) is required.')
folder = root / 'build'
folder.mkdir(exist_ok=True)
target = folder / ('libgnss_distance.dylib' if sys.platform == 'darwin' else 'libgnss_distance.so')
mode = '-dynamiclib' if sys.platform == 'darwin' else '-shared'
subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', mode, '-fPIC', str(root / 'native/distance.c'), '-lm', '-o', str(target)], check=True)
print(target.name)
