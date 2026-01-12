# Bulky Cache & Logs Policy

## Cache Policies

### Thumbnail Cache
- **Location**: `~/.cache/bulky/thumbnails/`
- **TTL**: Until file is modified (checks mtime)
- **Max size**: 50 MB (implementation: auto-prune oldest on exceed)
- **Invalidation**: On file modification detected

### Regex Compilation Cache
- **Mechanism**: `functools.lru_cache(maxsize=32)` in-memory
- **TTL**: Lifetime of application instance
- **Scope**: Up to 32 unique regex patterns cached
- **Invalidation**: LRU policy (oldest unused evicted)

## Logging Policies

### Log Level
- **Default**: WARNING (user-facing errors only)
- **Debug Mode**: DEBUG (set via `BULKY_DEBUG=1` env var)
- **Production**: ERROR (silent unless critical failure)

### Log Output
- **Destination**: stderr (allows user redirection)
- **Format**: `LEVEL: message` (simple, parseable)
- **No file rotation**: Single stderr stream (managed by session manager)

### Log Retention
- **Session-based**: Logs cleared on application exit
- **User responsibility**: Pipe to file if archival needed
  - Example: `bulky 2> ~/bulky_debug.log`

## Future Enhancements

1. **Persistent cache**: Store thumbnails with LRU eviction
2. **Syslog integration**: For deployment in headless environments
3. **Metrics export**: Prometheus-compatible metrics endpoint
4. **Performance budgets**: Alert if operation exceeds thresholds

## Environment Variables

```bash
BULKY_DEBUG=1           # Enable DEBUG logging
BULKY_TELEMETRY=1       # Enable performance markers
BULKY_CACHE_DIR=/tmp    # Override cache directory
BULKY_LOGLEVEL=DEBUG    # Set explicit log level
```

## Testing Cache Policies

```bash
# Enable telemetry to measure performance
BULKY_TELEMETRY=1 python3 usr/lib/bulky/bulky.py

# Check cache directory
ls -lah ~/.cache/bulky/thumbnails/ || echo "No cache yet"

# Run tests with debug logging
BULKY_DEBUG=1 python3 -m unittest tests.test_bulky -v
```
