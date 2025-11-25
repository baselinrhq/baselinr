# Prompt Engineering Guide

This guide explains how prompts are constructed for LLM explanations and how they can be customized.

## Prompt Structure

Each alert type (drift, anomaly, schema change) has a dedicated prompt construction function that formats technical details into a clear prompt for the LLM.

## System Prompt

All explanations use a consistent system prompt that establishes the LLM's role:

```
You are a data quality analyst explaining anomalies to data engineers and business users.

Your goal is to:
1. Clearly explain what happened in plain English
2. Provide context about why this might have occurred
3. Suggest potential next steps or areas to investigate
4. Be concise (2-4 sentences maximum)
5. Avoid jargon unless necessary

Format your response as a clear, actionable explanation.
```

## Drift Detection Prompts

Drift prompts include:
- Table and column names
- Metric name and values (baseline vs current)
- Change percentage or absolute change
- Severity level
- Timestamps
- Statistical test results (if available)

**Example Prompt:**
```
A data drift alert was detected:

Table: orders
Column: order_amount
Alert Type: Statistical Drift
Metric: mean
Severity: HIGH

Current value: 127.50
Baseline value: 98.20
Change: +30.00%

Baseline time: 2025-01-14T14:30:00
Current time: 2025-01-15T14:30:00

Test: Kolmogorov-Smirnov test
p-value: 0.003

Explain this drift in 2-4 clear sentences for a data engineer.
```

## Anomaly Detection Prompts

Anomaly prompts include:
- Table and column names
- Expected vs actual values
- Deviation score
- Anomaly type and detection method
- Severity level
- Method-specific context (control limits, IQR, etc.)

**Example Prompt:**
```
An anomaly was detected:

Table: orders
Column: order_amount
Metric: mean
Anomaly Type: control_limit_breach
Detection Method: control_limits
Severity: HIGH

Expected value: 100.0
Actual value: 150.0
Deviation: 2.50 standard deviations from expected

Control limits: [80.00, 120.00]

Explain this anomaly in 2-4 clear sentences for a data engineer.
```

## Schema Change Prompts

Schema change prompts include:
- Table name
- Change type (column_added, column_removed, type_changed, etc.)
- Column name (if applicable)
- Type changes (old → new)
- Severity level

**Example Prompt:**
```
A schema change was detected:

Table: orders
Change Type: column_added
Severity: MEDIUM

Column: new_column
Type change: None → varchar(255)

A new column was added to the table.

Explain the impact of this schema change in 2-4 clear sentences for a data engineer.
```

## Customization (Future)

Currently, prompts are fixed. Future versions may support:
- Custom system prompts
- Prompt templates per alert type
- User-defined prompt variables

## Prompt Best Practices

1. **Include context** - More context leads to better explanations
2. **Be specific** - Include exact values, not just "changed"
3. **Include timestamps** - Helps LLM understand temporal context
4. **Include severity** - Guides LLM on explanation tone
5. **Keep it concise** - LLM is instructed to be brief (2-4 sentences)

## Token Usage

Typical prompt sizes:
- Drift prompts: ~200-300 tokens
- Anomaly prompts: ~150-250 tokens
- Schema change prompts: ~100-150 tokens

Response sizes:
- Explanations: ~50-150 tokens (target: 2-4 sentences)

Total per explanation: ~250-450 tokens

