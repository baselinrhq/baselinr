# Baselinr Chat - Example Conversations

This document shows example conversations demonstrating the capabilities of the Baselinr Chat interface.

## Basic Profiling Queries

### What's been profiled?

```
🧑 You: What tables have been profiled recently?

🤖 Baselinr: I found 5 tables profiled in the last 7 days:

1. **orders** - Last profiled 2 hours ago
   - 2.3M rows, 15 columns
   - No active alerts

2. **customers** - Last profiled 3 hours ago
   - 450K rows, 22 columns
   - 1 HIGH severity drift alert on email column

3. **products** - Last profiled yesterday
   - 15K rows, 8 columns
   - No active alerts

4. **transactions** - Last profiled yesterday
   - 8.5M rows, 12 columns
   - 2 MEDIUM severity anomalies

5. **sessions** - Last profiled 6 hours ago
   - 125M rows, 9 columns
   - No active alerts

Would you like me to investigate any of these alerts?
```

### Get table details

```
🧑 You: Show me the profile for the customers table

🤖 Baselinr: Here's the detailed profile for the **customers** table:

**Table:** customers
**Schema:** public
**Last Profiled:** 2024-01-15 14:32:00 UTC
**Row Count:** 450,234
**Columns:** 22

**Column Summary:**

| Column | Type | Null Rate | Distinct Count |
|--------|------|-----------|----------------|
| customer_id | integer | 0.0% | 450,234 |
| email | varchar | 15.0% 🔴 | 445,123 |
| first_name | varchar | 0.5% | 8,234 |
| last_name | varchar | 0.4% | 12,456 |
| created_at | timestamp | 0.0% | 450,234 |
| phone | varchar | 22.0% | 389,000 |
| address | varchar | 8.0% | 421,000 |
| ... | ... | ... | ... |

**Health Assessment:**
- Status: ⚠️ Warning
- Issues: High null rate (15%) in email column
- Warnings: Elevated null rate (22%) in phone column

Would you like me to investigate the email column null rate issue?
```

## Drift Investigation

### Check for drift

```
🧑 You: Show me high severity drift events

🤖 Baselinr: I found 2 HIGH severity drift events in the last 7 days:

**1. customers.email - Null Rate Spike**
🔴 Severity: HIGH
- Started: 2024-01-15 02:47 UTC
- Baseline: 2.0%
- Current: 15.0%
- Change: +650%

**2. transactions.amount - Mean Shift**
🔴 Severity: HIGH
- Started: 2024-01-14 08:15 UTC
- Baseline: $127.50
- Current: $85.30
- Change: -33%

Would you like me to investigate either of these in detail?
```

### Deep dive into a specific issue

```
🧑 You: Tell me about the email column drift in customers

🤖 Baselinr: The **customers.email** column has a HIGH severity drift alert:

**What happened:**
The null rate increased from 2% to 15% starting at 2:47 AM UTC today.

**Analysis:**
- 2,341 records affected
- All null emails are from domain '@newpartner.com'
- This started after a pipeline deployment at 2:45 AM UTC

**Historical context:**
Looking at the last 90 days:
- Min null rate: 1.8%
- Max null rate: 2.5%
- Average: 2.1%
- Current (15%) is 7x above the historical maximum

**Related events:**
I found 2 related events around the same time:
1. orders.customer_id - Distinct count dropped 8% at 2:48 AM
2. sessions.user_id - Null rate increased from 1% to 7% at 2:50 AM

**Recommended actions:**
1. Check the partner integration code deployed at 2:45 AM
2. Review data validation in the new onboarding flow
3. Verify upstream data pipeline integrity

Would you like me to check the lineage for this table?
```

## Trend Analysis

### Historical trends

```
🧑 You: Show me the trend for order amounts over the last month

🤖 Baselinr: Here's the trend for **orders.order_amount** (mean) over the last 30 days:

**Trend Summary:**
- Data points: 30
- Min: $78.50
- Max: $127.30
- Mean: $102.45
- Trend: 📈 Stable

**Pattern Analysis:**
- Baseline: $98-105 on regular weekdays
- Weekends: Consistently 15-20% lower ($80-85)
- Black Friday (Nov 24): Peak at $127 (+30% above baseline)

**Key Observations:**
1. ✅ Stable weekday pattern with low variance (σ = $5.20)
2. ✅ Clear weekly seasonality (expected weekend dips)
3. ✅ Recent spike aligns with promotional calendar
4. ✅ No concerning anomalies outside expected events

**Current Status:**
Today's value ($102) is within normal range for a Tuesday.

Would you like me to compare this to other metrics like order count?
```

## Comparison Queries

### Compare runs

```
🧑 You: Compare the last two runs of customers

🤖 Baselinr: Comparing the last two profiling runs for **customers**:

**Run 1:** 2024-01-15 14:32 UTC (most recent)
**Run 2:** 2024-01-14 14:35 UTC

**Overall Changes:**
- Row count: 450,234 → 450,234 (0 change)
- Column count: 22 → 22 (no change)

**Significant Column Changes:**

| Column | Metric | Previous | Current | Change |
|--------|--------|----------|---------|--------|
| email | null_ratio | 2.0% | 15.0% | +650% 🔴 |
| phone | null_ratio | 20.5% | 22.0% | +7.3% 🟡 |
| last_login | null_ratio | 5.0% | 5.2% | +4.0% |
| address | distinct | 418,000 | 421,000 | +0.7% |

**Analysis:**
The most notable change is the email null rate spike (+650%).
Other changes are within normal fluctuation ranges.

Want me to investigate the email null rate issue further?
```

## Discovery and Search

### Find tables

```
🧑 You: Search for tables with 'order' in the name

🤖 Baselinr: I found 4 tables matching "order":

1. **orders** (public)
   - Last profiled: 2 hours ago
   - 2,345,678 rows, 15 columns
   - Status: ✅ Healthy

2. **order_items** (public)
   - Last profiled: 2 hours ago
   - 8,234,567 rows, 8 columns
   - Status: ⚠️ 1 warning

3. **order_history** (analytics)
   - Last profiled: 1 day ago
   - 15,678,234 rows, 12 columns
   - Status: ✅ Healthy

4. **order_backups** (archive)
   - Last profiled: 7 days ago
   - 45,234,123 rows, 15 columns
   - Status: 🟡 Stale (7 days since last run)

Would you like details on any of these tables?
```

### Check lineage

```
🧑 You: What are the upstream sources for orders?

🤖 Baselinr: Here's the lineage for **orders**:

**Upstream Sources (2 levels):**
```
raw_transactions (external)
  └─→ stg_transactions (staging)
        └─→ orders (public)
                    
raw_customers (external)
  └─→ stg_customers (staging)
        └─→ orders (public)
```

**Details:**

| Source Table | Type | Last Synced | Health |
|--------------|------|-------------|--------|
| raw_transactions | External | 1 hour ago | ✅ |
| stg_transactions | dbt model | 1 hour ago | ✅ |
| raw_customers | External | 2 hours ago | ⚠️ |
| stg_customers | dbt model | 2 hours ago | ⚠️ |

**Downstream Dependents:**
- analytics.daily_orders_summary
- reports.weekly_revenue
- ml.order_predictions

The ⚠️ warning on customer-related tables may be related to the email issue we discussed earlier.

Would you like me to check the downstream impact?
```

## Multi-Table Investigation

### Pattern analysis

```
🧑 You: Are there any patterns in the recent anomalies?

🤖 Baselinr: I analyzed all anomalies from the past 7 days and found an interesting pattern:

**Correlated Anomalies Detected:**

At 2:45-2:50 AM UTC on January 15:
1. **customers.email** - Null rate spiked (2% → 15%) ⏱️ 2:47 AM
2. **orders.customer_id** - Distinct count dropped 8% ⏱️ 2:48 AM
3. **sessions.user_id** - Null rate increased (1% → 7%) ⏱️ 2:50 AM

**Root Cause Analysis:**
All three anomalies started within 5 minutes of each other, right after a pipeline deployment at 2:45 AM. This suggests an upstream data quality issue in the customer identification pipeline.

**Impact Assessment:**
- 2,341 customer records with missing emails
- 892 orders with invalid customer references
- 4,567 sessions with missing user tracking

**Confidence:** 92% (based on temporal correlation and lineage)

**Recommended Actions:**
1. Review pipeline deployment from 2:45 AM UTC
2. Check customer ID resolution logic
3. Validate email parsing in integration layer
4. Consider rolling back if issues persist

Would you like me to create a summary report of this incident?
```

## Session Management

### Check stats

```
🧑 You: /stats

🤖 Baselinr:

**Session Statistics:**
| Metric | Value |
|--------|-------|
| Session ID | abc12345 |
| Duration | 5m 32s |
| Messages | 12 |
| Tool Calls | 8 |
| Tokens Used | 4,523 |
| Est. Cost | $0.0007 |
```

### Clear and start fresh

```
🧑 You: /clear

✓ Conversation history cleared
```

## Tips for Effective Queries

1. **Be specific** - "Show drift in the orders.amount column" is better than "show me drift"
2. **Use table names** - Mentioning specific tables helps the agent find relevant data faster
3. **Ask follow-ups** - The agent remembers context, so "tell me more about that" works
4. **Use time frames** - "in the last week" or "since yesterday" helps narrow results
5. **Request comparisons** - The agent can compare runs, tables, or time periods
