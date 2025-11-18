# Retry & Recovery - Quick Start

## What's Been Added

Baselinr now automatically retries transient warehouse failures with exponential backoff, structured logging, event emission, and Prometheus metrics.

## 🚀 Quick Start

### 1. Configuration (Already Enabled!)

Retry is **enabled by default** with sensible defaults:

```yaml
retry:
  enabled: true           # Already on!
  retries: 3              # Max retry attempts
  backoff_strategy: exponential
  min_backoff: 0.5        # 0.5 seconds
  max_backoff: 8.0        # 8 seconds max
```

### 2. Run Profiling

```bash
# Retry automatically handles transient errors
baselinr profile --config examples/config.yml
```

### 3. Check Logs

Watch for retry attempts in logs:

```json
{
  "event": "retry_attempt",
  "level": "warning",
  "attempt": 2,
  "error": "Connection timeout",
  "backoff_seconds": 1.12
}
```

## 🎯 What Gets Retried

### ✅ Automatic Retry (Transient Errors)
- Connection timeouts
- Connection lost/reset
- Network errors
- Rate limits
- Deadlocks
- Temporary unavailability

### ❌ No Retry (Permanent Errors)
- Syntax errors
- Authentication failures
- Permission denied
- Table not found
- Data type errors

## 📊 Monitoring

### Structured Logs
```bash
# Watch retry activity
tail -f baselinr.log | grep retry_attempt
```

### Prometheus Metrics
```promql
# Rate of retries
rate(baselinr_warehouse_transient_errors_total[5m])
```

### Event Bus
```python
# Subscribe to retry events
@event_bus.subscribe("retry_attempt")
def handle_retry(event):
    print(f"Retry: {event.metadata['function']}")
```

## 🔧 Tuning for Your Environment

### Production (Stable Warehouse)
```yaml
retry:
  retries: 3
  min_backoff: 0.5
  max_backoff: 8.0
```

### Production (Flaky Network)
```yaml
retry:
  retries: 5
  min_backoff: 1.0
  max_backoff: 16.0
```

### Development/Testing
```yaml
retry:
  retries: 1
  min_backoff: 0.1
  max_backoff: 1.0
```

### Disable Retry
```yaml
retry:
  enabled: false
```

## 📖 Full Documentation

**Comprehensive Guide:** [`docs/guides/RETRY_AND_RECOVERY.md`](docs/guides/RETRY_AND_RECOVERY.md)

**Topics Covered:**
- Configuration options
- Error classification details
- Observability (logs, events, metrics)
- Best practices
- Troubleshooting
- Performance impact
- Programmatic usage

## 🧪 Testing

```bash
# Run retry tests
pytest tests/utils/test_retry.py -v

# Test with your config
baselinr profile --config examples/config.yml
```

## 💡 Key Features

✅ **Exponential backoff** - Delays increase: 0.5s → 1s → 2s → 4s → 8s  
✅ **Jitter** - ±15% randomization prevents thundering herd  
✅ **Intelligent classification** - Distinguishes transient from permanent errors  
✅ **Graceful degradation** - Failed tables don't abort the run  
✅ **Full observability** - Logs + Events + Metrics  
✅ **Zero configuration** - Works out of the box  

## 🤔 Common Questions

**Q: Will retry slow down my profiling?**  
A: Only if errors occur. Successful operations have ~0.1ms overhead (negligible).

**Q: Can I retry specific operations only?**  
A: Retry applies to all warehouse operations. Use `enabled: false` to disable globally.

**Q: How do I know if retry is working?**  
A: Check logs for `retry_attempt` events or monitor the `baselinr_warehouse_transient_errors_total` metric.

**Q: What if I want different retry config per table?**  
A: Currently retry config is global. Per-table config is a future enhancement.

## 🆘 Troubleshooting

**Problem:** Profiling taking too long  
**Solution:** Reduce `retries` or `max_backoff`

**Problem:** Still getting connection errors  
**Solution:** Increase `retries` or check warehouse health

**Problem:** Want to see retry in action  
**Solution:** Set log level to DEBUG and watch for retry events

## 📚 Related Docs

- [Installation Guide](docs/getting-started/INSTALL.md)
- [Configuration Schema](docs/architecture/PROJECT_OVERVIEW.md)
- [Event System](docs/architecture/EVENTS_AND_HOOKS.md)
- [Prometheus Metrics](docs/guides/PROMETHEUS_METRICS.md)

---

**Ready to use!** Retry is enabled by default. Your profiling is now more resilient. 🎉

