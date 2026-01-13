# Development Guide for Bulky

## Quick Start

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt-get install python3-gi gir1.2-gtk-3.0 python3-setproctitle python3-unidecode

# For development
pip3 install --user pytest pylint
```

### Running from source
```bash
python3 usr/lib/bulky/bulky.py
```

### Running tests
```bash
make test-syntax    # Check syntax
make test           # Run unit tests
make lint           # Lint code
make clean          # Clean artifacts
```

## Code Quality Standards

### Before submitting PR:
1. **Syntax**: `make test-syntax` must pass
2. **Tests**: `make test` must pass (all tests green)
3. **Lint**: `make lint` should have minimal warnings
4. **Logging**: Use `logger.*()` instead of `print()` (see Onda 1)
5. **Error handling**: No bare `except:` clauses
6. **Git**: Add `.gitignore` entries for new artifacts

### Performance Considerations
- Check [PERFORMANCE_BUDGETS.md](PERFORMANCE_BUDGETS.md) for thresholds
- Enable `BULKY_TELEMETRY=1` to measure operations
- Test with 100+ files to catch O(n²) bugs
- Regex patterns are cached; check hit rate with debug logging

## Architecture Overview

### Main Components
- **FileObject** (lines 67-177): Wrapper around GLib/Gio file handles
- **MainWindow** (lines 201-821): GTK3 UI and rename operations
- **MyApplication** (lines 189-202): Gtk.Application lifecycle

### Key Workflows
1. **Add files**: `add_file()` → creates FileObject → updates TreeView
2. **Preview renames**: `on_widget_change()` → applies operation function → updates COL_NEW_NAME
3. **Execute renames**: `on_rename_button()` → validates → renames in filesystem → updates UI

### Rename Operations
Functions passed to `operation_function`:
- `replace_text()`: Find & replace with regex support
- `remove_text()`: Remove substring by position
- `insert_text()`: Insert text with auto-increment
- `change_case()`: Uppercase/lowercase/titlecase
- Wildcard patterns supported via glob syntax

## Testing Strategy

### Unit Tests (tests/test_bulky.py)
- Text operations (remove, insert, replace, case)
- File operations (create, rename, batch)
- Regex caching (lru_cache validation)
- No GTK dependencies (pure Python logic)

### Manual/Integration Tests
1. Add files from various locations (local, removable media, SMB share)
2. Test each operation function independently
3. Test combinations (e.g., replace + insert + case)
4. Test with special characters (emoji, quotes, spaces)
5. Test error cases (read-only directories, missing files)

### Performance Testing
```bash
# Enable telemetry markers
export BULKY_TELEMETRY=1
python3 usr/lib/bulky/bulky.py

# Check logs for timing data
# Look for elapsed_ms() markers in code
```

## Common Workflows

### Adding a new rename operation
1. Create function: `def my_operation(self, index, string) -> str:`
2. Add UI controls in Glade (bulky.ui)
3. Connect signal in `__init__`: `widget.connect("...", self.on_widget_change)`
4. Add to operation menu or radio buttons
5. Test with `make test`

### Optimizing performance
1. Check baseline: `BULKY_TELEMETRY=1 python3 usr/lib/bulky/bulky.py`
2. Profile: `python3 -m cProfile -s cumtime usr/lib/bulky/bulky.py`
3. Identify hotspot (function, file operation, loop)
4. Implement optimization (cache, lazy load, batch)
5. Measure improvement: re-run baseline, compare
6. Add test case to prevent regression

### Debugging issues
```bash
# Enable debug logging
export BULKY_DEBUG=1
python3 usr/lib/bulky/bulky.py 2>&1 | grep -E "WARNING|ERROR|DEBUG"

# Check for exceptions
python3 -u usr/lib/bulky/bulky.py 2>&1
```

## Release Checklist

Before releasing new version:
- [ ] `git log` shows meaningful commit messages
- [ ] `make test` passes on Python 3.9+
- [ ] `make lint` shows <5 warnings
- [ ] README.md updated (if needed)
- [ ] Version bump in debian/changelog
- [ ] Performance budgets still met (run baseline)
- [ ] CHANGELOG entry (optional, link to commits)

## Documentation

- **PERFORMANCE_BUDGETS.md**: Performance targets and measurement
- **CACHE_LOGS_POLICY.md**: Caching and logging strategy
- **Makefile**: Common build/test targets
- **.github/workflows/ci.yml**: Automated testing

## Getting Help

- Check existing issues on GitHub
- Review code comments (look for WARNING, NOTE comments)
- Run tests with `-v` flag for verbose output
- Enable `BULKY_DEBUG=1` for structured logging
