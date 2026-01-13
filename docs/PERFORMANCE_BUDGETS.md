# Bulky Performance Budgets

## Objectives
Define acceptable performance thresholds to catch regressions and guide optimization.

## Metrics & Targets

### Startup
- **Target**: < 2 seconds (cold start, first window)
- **Measurement**: `time python3 -c "from gi.repository import Gtk; import bulky; ..."`
- **Current baseline** (v4.1, post-Onda2): ~1.5s estimated
- **Threshold**: Warn if exceeds 2.5s

### File Addition (per file, UI responsive)
- **Target**: < 100ms per file (including thumbnail generation)
- **Measurement**: Time to add N files and update UI
- **Current baseline**: ~50-100ms (depends on FS speed)
- **Threshold**: Warn if exceeds 150ms

### Rename Operation (per file)
- **Target**: < 50ms per file rename (kernel syscall limited)
- **Measurement**: Total time / count(files)
- **Current baseline**: ~10-30ms (filesystem bound)
- **Threshold**: Warn if exceeds 100ms

### Memory Usage
*Start time*: target 2s on reference workstation (GTK available).
*Idle RAM*: target 80 MB with GUI idle and no selection.
*Headless smoke*: <200 ms for single rename (scripts/smoke_headless.py).
*Cache/log size*: <100 MB total (respect BULKY_CACHE_DIR; thumbnails cleaned periodically).
*Rename throughput*: target 5k files < 5s on SSD; per-file avg < 1 ms (telemetry).
- **Expected**: Most users reuse 3-5 patterns in one session
### CI Pipeline (Future)
```yaml
- Run performance baseline suite
- Compare: startup_time, memory_peak, rename_throughput
- Alert if regression > 10%
- Block merge if regression > 20%
```

### Manual Testing
```bash
# Before optimization
time python3 usr/lib/bulky/bulky.py < /dev/null

# After optimization
time python3 usr/lib/bulky/bulky.py < /dev/null

# Compare results
```

## Optimization Priority

| Priority | Metric | ROI | Effort | Status |
|----------|--------|-----|--------|--------|
| **High** | Regex cache (P4) | 30-50% cache hits | Low | ✅ Done (Onda 2) |
| **High** | Lazy-load UI | ~500ms save | Medium | TODO (Onda 3+) |
| **Medium** | Thumbnail cache (persistent) | ~200ms per file | Medium | Planned |
| **Medium** | Batch rename async | UI responsiveness | High | Planned |
| **Low** | Code profiling | Unknown | High | Backlog |

## Measurement Tools

### Python Profiling
```bash
python3 -m cProfile -s cumulative usr/lib/bulky/bulky.py
```

### Memory Profiling
```bash
pip3 install memory_profiler
python3 -m memory_profiler usr/lib/bulky/bulky.py
```

### Timing (Environment Variables)
```bash
BULKY_TELEMETRY=1 python3 usr/lib/bulky/bulky.py
# Logs timing markers for key operations
```

## Success Criteria for Optimization Waves

- **Onda 2**: Regex cache active, unit tests passing ✅
- **Onda 3**: Telemetry infrastructure in place, baseline captured
- **Onda 4**: CI pipeline running, performance budgets enforced
