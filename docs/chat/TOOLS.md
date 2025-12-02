# Baselinr Chat - Available Tools

The chat agent has access to the following tools for querying your data quality monitoring system.

## Profiling Tools

### query_recent_runs

Query recent profiling runs to see what tables have been profiled.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | No | Filter by table name |
| schema | string | No | Filter by schema name |
| limit | integer | No | Maximum runs to return (default: 10) |
| days | integer | No | Look back days (default: 7) |
| status | string | No | Filter by status (completed, failed) |

**Example questions:**
- "What tables have been profiled recently?"
- "Show me runs for the orders table"
- "List failed profiling runs from the last week"

### get_table_profile

Get detailed profile for a specific table including all column metrics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | Yes | Table name |
| run_id | string | No | Specific run ID (latest if not provided) |

**Example questions:**
- "Show me the profile for the customers table"
- "What metrics do we have for orders?"
- "Get detailed info about the products table"

## Drift & Anomaly Tools

### query_drift_events

Query drift detection events to find significant data changes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | No | Filter by table name |
| column | string | No | Filter by column name |
| severity | string | No | Filter by severity (low, medium, high) |
| days | integer | No | Look back days (default: 7) |
| limit | integer | No | Maximum events to return (default: 20) |

**Example questions:**
- "Show me high severity drift events"
- "What drift has occurred in the customers table?"
- "Are there any drift issues with the email column?"

### query_anomalies

Query anomaly detection events to find unusual data patterns.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | No | Filter by table name |
| column | string | No | Filter by column name |
| metric | string | No | Filter by metric (null_rate, mean, distinct_count) |
| days | integer | No | Look back days (default: 7) |
| limit | integer | No | Maximum anomalies to return (default: 20) |

**Example questions:**
- "What anomalies have been detected?"
- "Show me null rate anomalies in the orders table"
- "Are there any issues with the customer_id column?"

## Trend & History Tools

### get_column_history

Get historical trend for a specific column metric over time.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | Yes | Table name |
| column | string | Yes | Column name |
| metric | string | Yes | Metric to track (mean, null_ratio, distinct_count) |
| days | integer | No | Days of history (default: 30) |

**Example questions:**
- "Show me the trend for order_amount mean over the last month"
- "How has the null rate for email changed?"
- "Get the history of distinct_count for customer_id"

### compare_runs

Compare two profiling runs to see what changed between them.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | Yes | Table name |
| run_id_1 | string | No | First run ID (latest if not provided) |
| run_id_2 | string | No | Second run ID (second latest if not provided) |

**Example questions:**
- "Compare the last two runs for orders"
- "What changed between the most recent profiles of customers?"
- "Show me the differences in the products table"

## Discovery Tools

### search_tables

Search for tables by name or schema pattern.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query (matches table or schema name) |
| limit | integer | No | Maximum results (default: 20) |

**Example questions:**
- "Find tables with 'order' in the name"
- "Search for customer-related tables"
- "What tables are in the analytics schema?"

### get_lineage

Get data lineage (upstream sources and downstream dependents) for a table.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | string | Yes | Table name |
| schema | string | No | Schema name |
| direction | string | No | Lineage direction (upstream, downstream, both) |
| max_depth | integer | No | Maximum depth to traverse (default: 2) |

**Example questions:**
- "What are the upstream sources for orders?"
- "Show me downstream tables that depend on customers"
- "Get the lineage for the transactions table"

## Tool Usage Tips

1. **Tools are called automatically** - You don't need to specify which tool to use; the agent chooses based on your question

2. **Multiple tools per query** - The agent may use several tools to answer a complex question

3. **Context is maintained** - The agent remembers previous tool results when answering follow-up questions

4. **Caching** - Tool results are cached within a session for faster subsequent queries

5. **Verbose mode** - Use `/verbose` to see which tools are being called

## Extending Tools

The tool system is extensible. See the developer documentation for how to add custom tools for your specific use cases.
