#!/usr/bin/env python3
import os
import sys
import time
import tempfile
import shutil
import importlib.util
import subprocess
from statistics import mean

ROOT = os.path.dirname(os.path.abspath(__file__))


def measure_import_time(n=5):
    times = []
    for _ in range(n):
        t0 = time.time()
        spec = importlib.util.spec_from_file_location('bulky_mod', os.path.join(ROOT, 'usr', 'lib', 'bulky', 'bulky.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        dt = (time.time() - t0) * 1000.0
        times.append(dt)
        # Force module removal for next iteration (cold-ish import)
        if 'bulky_mod' in sys.modules:
            del sys.modules['bulky_mod']
        time.sleep(0.05)
    return min(times), mean(times), max(times)


def measure_rename_throughput(n_files=500):
    tmp = tempfile.mkdtemp(prefix='bulky_bench_')
    try:
        # Create files
        for i in range(n_files):
            with open(os.path.join(tmp, f'file_{i:05d}.txt'), 'w') as f:
                f.write('x')
        # Rename
        t0 = time.time()
        for i in range(n_files):
            src = os.path.join(tmp, f'file_{i:05d}.txt')
            dst = os.path.join(tmp, f'renamed_{i:05d}.txt')
            os.rename(src, dst)
        total = (time.time() - t0)
        per_file_ms = (total / n_files) * 1000.0
        thr_files_s = n_files / total if total > 0 else float('inf')
        return per_file_ms, thr_files_s, n_files
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def measure_memory_import():
    cmd = [
        '/usr/bin/time','-v','python3','-c',
        'import importlib.util,sys;import time;spec=importlib.util.spec_from_file_location("bulky_mod","usr/lib/bulky/bulky.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);print("OK")'
    ]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        rss = None
        for line in out.stderr.splitlines():
            if 'Maximum resident set size' in line:
                rss = int(line.split(':')[-1].strip())
                break
        return rss
    except Exception:
        return None


def main():
    print('Bulky micro-benchmarks')
    print('ROOT:', ROOT)

    print('\n[1] Startup (module import)')
    tmin, tavg, tmax = measure_import_time(n=5)
    print(f'  import_time_ms: min={tmin:.2f} avg={tavg:.2f} max={tmax:.2f}')

    print('\n[2] Memory (import)')
    rss = measure_memory_import()
    if rss is not None:
        print(f'  max_rss_kb: {rss}')
    else:
        print('  max_rss_kb: n/a')

    print('\n[3] Rename throughput (filesystem)')
    per_file_ms, thr, n = measure_rename_throughput(n_files=500)
    print(f'  files: {n}, per_file_ms: {per_file_ms:.3f}, throughput_files_per_s: {thr:.2f}')


if __name__ == '__main__':
    main()
