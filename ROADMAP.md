# 🗺️ Baselinr Roadmap

This document outlines the planned development direction for Baselinr. Priorities may shift based on community feedback.

> **We'd love your input!** [Open an issue](https://github.com/baselinrhq/baselinr/issues) to suggest features or vote on what matters most to you.

---

## 🎯 Current Focus (Q1 2025)

### Smart Recommendations
- [ ] Improved table prioritization based on query patterns and lineage
- [ ] Column-level check recommendations with confidence scoring
- [ ] Auto-apply mode for zero-touch initial setup

### Alerting & Notifications
- [ ] Native Slack integration with configurable alert channels
- [ ] Email notifications for drift and validation failures
- [ ] PagerDuty integration for critical alerts

### Quality Studio UI
- [ ] Improved onboarding flow
- [ ] Light mode support
- [ ] Saved views and custom dashboards

---

## 🔮 Near-Term (Q2 2025)

### Advanced Drift Detection
- [ ] ML-based anomaly detection (beyond statistical tests)
- [ ] Drift trend analysis over time
- [ ] Auto-tuning thresholds based on historical patterns

### Enhanced Lineage
- [ ] Visual lineage graph in Quality Studio
- [ ] Cross-warehouse lineage support

### Performance & Scale
- [ ] Connection pooling improvements

---

## 🌟 Future Considerations

- **Observability**: OpenTelemetry integration for profiling metrics (Prometheus metrics already available)
- **Multi-tenant**: Team-based access control in Quality Studio
- **SaaS Option**: Hosted version for teams who don't want to self-host

---

## ✅ Recently Completed

- [x] Quality Studio web UI
- [x] Statistical drift detection (KS, PSI, Chi-square)
- [x] Intelligent baseline selection
- [x] Root cause analysis
- [x] Anomaly detection with expectation learning
- [x] Data validation framework
- [x] Dagster and Airflow integrations
- [x] BigQuery and Redshift support
- [x] Parallel profiling for large table counts
- [x] Incremental profiling (only changed partitions)
- [x] Native ODCS (Open Data Contract Standard) support

---

## 💬 Have Ideas?

The best features come from real user needs. If you have ideas or pain points:

1. **Check existing issues** — Someone may have already suggested it
2. **Open a new issue** — Describe your use case and why it matters
3. **Vote with 👍** — React to issues you want prioritized

[→ View all feature requests](https://github.com/baselinrhq/baselinr/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
