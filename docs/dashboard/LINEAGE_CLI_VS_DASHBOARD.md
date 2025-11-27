# Lineage: CLI vs Dashboard Comparison

This document compares the existing CLI lineage features with the planned dashboard visualization capabilities.

## Overview

Baselinr already has **full lineage functionality** available through the CLI. The dashboard integration will provide a **visual, interactive interface** for the same data, making it more accessible and easier to explore.

---

## Feature Comparison Matrix

| Feature | CLI | Dashboard (Planned) | Notes |
|---------|-----|---------------------|-------|
| **View upstream dependencies** | ✅ `baselinr lineage upstream` | ✅ Interactive graph + list view | Dashboard adds visual exploration |
| **View downstream dependencies** | ✅ `baselinr lineage downstream` | ✅ Interactive graph + list view | Click to expand nodes |
| **Find path between tables** | ✅ `baselinr lineage path` | ✅ Path finder UI | Visual path highlighting |
| **List available providers** | ✅ `baselinr lineage providers` | ✅ Provider filter dropdown | Dashboard shows as filters |
| **Sync lineage from query history** | ✅ `baselinr lineage sync` | ❌ CLI only | Bulk sync stays in CLI |
| **Clean up stale lineage** | ✅ `baselinr lineage cleanup` | ❌ CLI only | Maintenance stays in CLI |
| **Column-level lineage** | ✅ Via SDK | ✅ Expandable graph view | Both available |
| **Root cause analysis (drift)** | ⚠️ Manual (run multiple commands) | ✅ One-click from drift alert | Major UX improvement |
| **Impact analysis** | ⚠️ Manual | ✅ Visual impact view | See affected downstream tables |
| **Search tables** | ⚠️ Via grep/flags | ✅ Real-time search bar | Much faster |
| **Filter by schema** | ✅ Via `--schema` flag | ✅ Dropdown filter | More intuitive |
| **Filter by provider** | ⚠️ Via API | ✅ Dropdown filter | Not available in CLI |
| **Filter by confidence** | ❌ No | ✅ Slider filter | New feature |
| **Export graph** | ✅ JSON/CSV via flags | ✅ SVG/PNG/JSON | More formats |
| **Visual graph layout** | ❌ ASCII/table only | ✅ Interactive DAG | Major improvement |
| **Zoom/pan graph** | ❌ No | ✅ Full interactivity | Dashboard only |
| **Color-code by drift** | ❌ No | ✅ Red nodes for drift | Dashboard only |
| **Lineage health metrics** | ⚠️ Scattered in output | ✅ KPI dashboard | Unified view |
| **Cross-reference with runs** | ⚠️ Manual | ✅ Automatic | One-click navigation |
| **Historical lineage changes** | ❌ No | ❌ Not in MVP | Future enhancement |

**Legend**:
- ✅ Fully supported
- ⚠️ Partially supported or cumbersome
- ❌ Not available

---

## CLI Commands → Dashboard Pages Mapping

### 1. Lineage Upstream

**CLI**:
```bash
baselinr lineage upstream --config config.yml --table customers --max-depth 3 --format json
```

**Dashboard**:
```
Navigate to: /lineage
Search: "customers"
Click: customers node
View: Upstream panel (auto-shows dependencies)
```

**Advantage**: Visual graph + one click vs typing command

---

### 2. Lineage Downstream

**CLI**:
```bash
baselinr lineage downstream --config config.yml --table raw.events --max-depth 2
```

**Dashboard**:
```
Navigate to: /lineage/raw.events
Tab: Downstream
View: Visual graph of 2-hop dependencies
```

**Advantage**: See entire dependency tree at once

---

### 3. Find Path

**CLI**:
```bash
baselinr lineage path --config config.yml --from raw.events --to analytics.revenue
```

**Dashboard**:
```
Navigate to: /lineage
Click: "Find Path" button
Enter: "raw.events" → "analytics.revenue"
View: Highlighted path in graph
```

**Advantage**: Visual path with all intermediary tables highlighted

---

### 4. Root Cause Analysis (Drift)

**CLI** (manual workflow):
```bash
# 1. Detect drift
baselinr drift detect --config config.yml --table customers

# 2. Get upstream lineage
baselinr lineage upstream --config config.yml --table customers --max-depth 2

# 3. Check each upstream table manually
baselinr runs --config config.yml --table raw.users
baselinr runs --config config.yml --table raw.events

# 4. Investigate drift in upstream
baselinr drift detect --config config.yml --table raw.users
```

**Dashboard** (automated workflow):
```
Navigate to: /drift
Click: Drift alert for "customers"
View: Root Cause Analysis panel
      - Shows upstream tables automatically
      - Highlights which have recent drift
      - One-click to investigate each
Click: "raw.users" → Navigate to lineage/drift view
```

**Advantage**: 10+ CLI commands → 2 clicks

---

### 5. Provider Information

**CLI**:
```bash
baselinr lineage providers --config config.yml
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Provider                 ┃ Status         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ dbt_manifest             │ Available      │
│ postgres_query_history   │ Available      │
│ sql_parser               │ Available      │
└──────────────────────────┴────────────────┘
```

**Dashboard**:
```
Navigate to: /lineage
View: Stats section shows provider breakdown
      - "142 edges from dbt_manifest"
      - "87 edges from postgres_query_history"
      - "23 edges from sql_parser"
Filter: Click provider name to show only those edges
```

**Advantage**: Visual breakdown + interactive filtering

---

### 6. Lineage Stats

**CLI**:
```bash
baselinr lineage upstream --table customers | wc -l  # Count upstream
baselinr lineage downstream --table customers | wc -l  # Count downstream
```

**Dashboard**:
```
Navigate to: /lineage
View: KPI cards
      - "Total Tables: 150"
      - "With Lineage: 142 (94.6%)"
      - "Total Edges: 387"
      - "Stale Edges: 12 (3.1%)"
      - Provider breakdown chart
```

**Advantage**: Unified metrics dashboard

---

## Use Case Comparison

### Use Case 1: "Show me what feeds into the `customers` table"

| Approach | Steps | Time |
|----------|-------|------|
| **CLI** | 1. Run `baselinr lineage upstream --table customers`<br>2. Read table output | ~30 sec |
| **Dashboard** | 1. Navigate to `/lineage`<br>2. Search "customers"<br>3. Click node | ~5 sec |

---

### Use Case 2: "I detected drift in `revenue` table - find the root cause"

| Approach | Steps | Time |
|----------|-------|------|
| **CLI** | 1. Run `baselinr lineage upstream --table revenue`<br>2. Manually check each upstream table<br>3. Run drift detection on each<br>4. Investigate suspicious tables<br>5. Repeat for 2nd-level upstream | ~5 min |
| **Dashboard** | 1. View drift alert<br>2. Click "Root Cause Analysis"<br>3. Dashboard shows upstream with drift indicators<br>4. Click suspicious table to investigate | ~30 sec |

**Impact**: **10x faster** drift investigation

---

### Use Case 3: "If I change `raw.events`, what will be affected?"

| Approach | Steps | Time |
|----------|-------|------|
| **CLI** | 1. Run `baselinr lineage downstream --table raw.events`<br>2. Count affected tables<br>3. Manually assess criticality | ~1 min |
| **Dashboard** | 1. Navigate to `/lineage/raw.events`<br>2. View "Impact Analysis" section<br>3. Dashboard shows count + list + severity indicators | ~10 sec |

---

### Use Case 4: "Find the path from `raw.events` to `analytics.revenue`"

| Approach | Steps | Time |
|----------|-------|------|
| **CLI** | 1. Run `baselinr lineage path --from raw.events --to analytics.revenue`<br>2. Read text output | ~20 sec |
| **Dashboard** | 1. Navigate to `/lineage`<br>2. Use "Find Path" tool<br>3. Visual path highlighted on graph | ~10 sec |

---

## When to Use CLI vs Dashboard

### Use CLI When:
- ✅ **Automation/scripting**: Integrate with CI/CD or automated workflows
- ✅ **Bulk operations**: Sync lineage, cleanup stale edges
- ✅ **Headless environments**: SSH into servers without GUI
- ✅ **Export to files**: Generate reports, feed to other tools
- ✅ **Quick lookups**: Single table query when dashboard isn't running

### Use Dashboard When:
- ✅ **Exploration**: Browsing lineage, discovering relationships
- ✅ **Drift investigation**: Root cause analysis workflow
- ✅ **Impact assessment**: Understanding downstream effects
- ✅ **Presentations**: Showing lineage to stakeholders
- ✅ **Visual learners**: Better understanding of complex dependencies
- ✅ **Cross-referencing**: Linking lineage with profiling/drift data

---

## Example Workflows

### Workflow 1: Weekly Lineage Health Check

**CLI** (for automation):
```bash
#!/bin/bash
# weekly_lineage_check.sh

# Sync lineage from query history
baselinr lineage sync --config config.yml --all

# Check for stale edges
baselinr lineage cleanup --config config.yml --dry-run

# Generate report
baselinr lineage upstream --table critical_table --format json > lineage_report.json
```

**Dashboard** (for review):
```
1. Navigate to /lineage
2. Review "Lineage Health" KPIs
3. Check stale edge count
4. Filter by provider to ensure coverage
5. Export graph for documentation
```

**Best Practice**: Use CLI for automation, Dashboard for review

---

### Workflow 2: Investigating Production Drift

**Scenario**: Drift detected in `daily_revenue` table at 9am production run

**CLI Approach** (manual, slow):
```bash
# Step 1: Confirm drift
baselinr drift detect --table daily_revenue --baseline-run prod-2025-11-26 --current-run prod-2025-11-27

# Step 2: Get upstream
baselinr lineage upstream --table daily_revenue --max-depth 2

# Step 3: Check each upstream manually
baselinr runs --table orders --limit 5
baselinr runs --table products --limit 5
baselinr runs --table users --limit 5

# Step 4: Detect drift in upstreams
baselinr drift detect --table orders ...
baselinr drift detect --table products ...
```

Time: ~5-10 minutes (lots of typing, context switching)

**Dashboard Approach** (visual, fast):
```
1. Open /drift page
2. Click on "daily_revenue" drift alert
3. View "Root Cause Analysis" panel
   → Sees 3 upstream tables: orders, products, users
   → Red indicator on "orders" (has drift too)
4. Click "orders" 
   → Navigates to orders lineage/drift page
   → Sees orders dropped 30% → likely root cause
5. Click "Investigate upstream"
   → Sees orders depends on raw.orders_api
   → Checks API logs for outage
```

Time: ~1 minute (2-3 clicks, visual indicators)

**Winner**: Dashboard is **5-10x faster** for investigation workflows

---

### Workflow 3: Onboarding New Team Member

**Task**: Explain how data flows from raw → staging → analytics

**CLI Approach**:
```bash
# Show them text output
baselinr lineage upstream --table analytics.revenue

# They need to mentally map relationships
# Hard to see big picture
```

**Dashboard Approach**:
```
1. Open /lineage page
2. Show interactive graph
3. Click on analytics.revenue
4. Visually trace upstream dependencies
5. Explain each layer: raw → staging → analytics
6. Click nodes to show details
```

**Winner**: Dashboard is much better for teaching/presentations

---

## Migration Path

Users won't need to migrate anything - both CLI and Dashboard will coexist:

```
┌─────────────────────────────────────────────┐
│           Lineage Data Storage              │
│    (baselinr_lineage tables in DB)         │
└────────────┬──────────────────┬─────────────┘
             │                  │
             │                  │
       ┌─────▼──────┐    ┌─────▼──────┐
       │    CLI     │    │  Dashboard │
       │            │    │            │
       │ • profile  │    │ • /lineage │
       │ • sync     │    │ • /drift   │
       │ • cleanup  │    │ • /tables  │
       └────────────┘    └────────────┘
```

- **Same data source**: Both read from `baselinr_lineage` table
- **Complementary**: CLI for automation, Dashboard for exploration
- **No breaking changes**: Existing CLI commands continue to work

---

## Summary

### CLI Strengths
- 🚀 **Automation**: Easy to script and integrate
- 📦 **Bulk operations**: Sync, cleanup, export at scale
- 🔌 **Headless**: Works over SSH, in CI/CD
- 📝 **Parseable output**: JSON/CSV for further processing

### Dashboard Strengths
- 👁️ **Visualization**: See entire lineage graph at once
- ⚡ **Speed**: 5-10x faster for investigation workflows
- 🔗 **Integration**: Links drift → lineage → runs seamlessly
- 🎯 **Accessibility**: Non-technical users can explore
- 📊 **Metrics**: Unified health dashboard

### Recommendation

**Use both!**
- **Data engineers**: Primarily CLI (automation) + Dashboard (investigation)
- **Analysts**: Primarily Dashboard (exploration)
- **Data scientists**: Dashboard for understanding, CLI for notebooks
- **Managers/stakeholders**: Dashboard (presentations, reports)

---

## Next Steps

1. ✅ CLI lineage already works → Start using it now!
2. 📋 Dashboard planning complete → Review [LINEAGE_INTEGRATION_PLAN.md](./LINEAGE_INTEGRATION_PLAN.md)
3. 🚀 Start implementation → Follow [LINEAGE_IMPLEMENTATION_CHECKLIST.md](./LINEAGE_IMPLEMENTATION_CHECKLIST.md)

---

**Last Updated**: 2025-11-27  
**Related Docs**:
- [Data Lineage Guide](/docs/guides/DATA_LINEAGE.md) - CLI usage
- [Dashboard Summary](./LINEAGE_DASHBOARD_SUMMARY.md) - Dashboard overview
- [Full Integration Plan](./LINEAGE_INTEGRATION_PLAN.md) - Implementation details
