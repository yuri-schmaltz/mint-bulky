#!/usr/bin/env python3
import os
import sys
import time
import shutil
import subprocess
import importlib.util

ROOT = os.path.dirname(os.path.abspath(__file__))
BULKY_PATH = os.path.join(ROOT, 'usr', 'lib', 'bulky', 'bulky.py')


def has_xvfb():
    return shutil.which('xvfb-run') is not None


def run_gui_once():
    t0 = time.time()
    code = r'''
import importlib.util, time
from gi.repository import Gio, GLib
spec = importlib.util.spec_from_file_location('bulky_mod', 'usr/lib/bulky/bulky.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
start = time.time()
class BenchApp(mod.MyApplication):
    def activate(self, application):
        super().activate(application)
        # Quit shortly after first activate; window already shown
        GLib.timeout_add(150, lambda: (self.quit(), False)[1])
app = BenchApp('org.x.bulky.bench', Gio.ApplicationFlags.FLAGS_NONE)
app.run()
print('BENCH_OK', int((time.time()-start)*1000))
'''
    env = os.environ.copy()
    env['LC_ALL'] = env.get('LC_ALL', 'C.UTF-8')
    if has_xvfb():
        cmd = ['xvfb-run', '-a', 'python3', '-c', code]
    else:
        # Try without X (may fail); allow graceful exit
        cmd = ['python3', '-c', code]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    dt = (time.time() - t0) * 1000.0
    ok = 'BENCH_OK' in p.stdout
    inline_ms = None
    if ok:
        try:
            inline_ms = int(p.stdout.strip().split('BENCH_OK')[-1].strip())
        except Exception:
            inline_ms = None
    return ok, dt, inline_ms, p.returncode, p.stderr.strip()


def run_gui_bench(iterations=3):
    results = []
    for _ in range(iterations):
        ok, wall_ms, inline_ms, rc, err = run_gui_once()
        results.append((ok, wall_ms, inline_ms, rc, err))
        time.sleep(0.1)
    return results


def summarize(results):
    ok_runs = [r for r in results if r[0]]
    if not ok_runs:
        return {
            'runs': len(results),
            'ok': 0,
            'note': 'No successful GUI runs (xvfb missing or GTK headless not permitted)',
        }
    wall = [r[1] for r in ok_runs]
    inline = [r[2] for r in ok_runs if r[2] is not None]
    return {
        'runs': len(results),
        'ok': len(ok_runs),
        'wall_ms_min': min(wall),
        'wall_ms_avg': sum(wall)/len(wall),
        'wall_ms_max': max(wall),
        'inline_ms_min': min(inline) if inline else None,
        'inline_ms_avg': (sum(inline)/len(inline)) if inline else None,
        'inline_ms_max': max(inline) if inline else None,
        'used_xvfb': has_xvfb(),
    }


def main():
    results = run_gui_bench()
    summary = summarize(results)
    print('GUI Benchmark Summary:')
    for k, v in summary.items():
        print(f'  {k}: {v}')
    if not summary.get('ok'):
        print('\nHint: Install xvfb to enable headless GUI benchmark:')
        print('  sudo apt-get install xvfb')

if __name__ == '__main__':
    main()
