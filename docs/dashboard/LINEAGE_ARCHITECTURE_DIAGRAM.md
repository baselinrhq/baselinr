# Lineage Dashboard Architecture Diagram

Visual reference for understanding how lineage data flows through the dashboard.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                               │
│                                                                          │
│  Browser → http://localhost:3000/lineage                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                               │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐          │
│  │ /app/lineage/  │  │ /app/tables/   │  │ /app/drift/     │          │
│  │   page.tsx     │  │ [table]/       │  │   page.tsx      │          │
│  │                │  │   page.tsx     │  │                 │          │
│  └────────┬───────┘  └────────┬───────┘  └─────────┬───────┘          │
│           │                   │                     │                   │
│           └───────────────────┼─────────────────────┘                   │
│                               │                                         │
│           ┌───────────────────▼───────────────────┐                    │
│           │   Components:                         │                    │
│           │   - LineageGraph.tsx (React Flow)    │                    │
│           │   - LineageStats.tsx                 │                    │
│           │   - LineageExplorer.tsx              │                    │
│           │   - DriftRootCausePanel.tsx          │                    │
│           └───────────────────┬───────────────────┘                    │
│                               │                                         │
│           ┌───────────────────▼───────────────────┐                    │
│           │   API Client (lib/api.ts)            │                    │
│           │   - fetchLineageGraph()              │                    │
│           │   - fetchTableLineage()              │                    │
│           │   - fetchLineagePath()               │                    │
│           └───────────────────┬───────────────────┘                    │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │
                                │ HTTP GET /api/lineage/*
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                │
│                      dashboard/backend/main.py                           │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ API Endpoints:                                                  │    │
│  │                                                                 │    │
│  │  GET /api/lineage/graph          → LineageGraphResponse        │    │
│  │  GET /api/lineage/table/{name}   → TableLineageResponse        │    │
│  │  GET /api/lineage/path           → LineagePathResponse         │    │
│  │  GET /api/lineage/stats          → LineageStatsResponse        │    │
│  │  GET /api/drift/{id}/lineage     → DriftLineageResponse        │    │
│  │                                                                 │    │
│  └───────────────────────────┬──────────────────────────────────────┘    │
│                              │                                           │
│  ┌───────────────────────────▼──────────────────────────────────────┐    │
│  │ dashboard/backend/lineage_queries.py                            │    │
│  │                                                                 │    │
│  │  class LineageQueries:                                          │    │
│  │    • get_lineage_graph()                                        │    │
│  │    • get_table_lineage()                                        │    │
│  │    • enrich_nodes_with_metrics()  ← joins with runs/drift      │    │
│  │                                                                 │    │
│  └───────────────────────────┬──────────────────────────────────────┘    │
│                              │                                           │
│                              │ Uses                                      │
│                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ baselinr/query/lineage_client.py                               │    │
│  │                                                                 │    │
│  │  class LineageQueryClient:                                      │    │
│  │    • get_upstream_tables()                                      │    │
│  │    • get_downstream_tables()                                    │    │
│  │    • get_lineage_path()                                         │    │
│  │    • get_all_lineage()                                          │    │
│  │    • get_upstream_columns()                                     │    │
│  │                                                                 │    │
│  └───────────────────────────┬──────────────────────────────────────┘    │
└────────────────────────────┼─────────────────────────────────────────────┘
                              │
                              │ SQL Queries
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATABASE                                       │
│                      (PostgreSQL / SQLite)                               │
│                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │ baselinr_lineage     │  │ baselinr_runs        │                    │
│  │                      │  │                      │                    │
│  │ • upstream_schema    │  │ • run_id             │                    │
│  │ • upstream_table     │  │ • dataset_name       │                    │
│  │ • downstream_schema  │  │ • profiled_at        │                    │
│  │ • downstream_table   │  │ • row_count          │                    │
│  │ • provider           │  │ • status             │                    │
│  │ • confidence_score   │  │                      │                    │
│  │ • last_seen_at       │  └──────────────────────┘                    │
│  │                      │                                               │
│  └──────────────────────┘  ┌──────────────────────┐                    │
│                            │ baselinr_events      │                    │
│  ┌──────────────────────┐  │                      │                    │
│  │baselinr_column_      │  │ • event_id           │                    │
│  │     lineage          │  │ • table_name         │                    │
│  │                      │  │ • drift_severity     │                    │
│  │ • upstream_column    │  │ • timestamp          │                    │
│  │ • downstream_column  │  │                      │                    │
│  │ • transformation     │  └──────────────────────┘                    │
│  │                      │                                               │
│  └──────────────────────┘                                               │
│                                                                          │
│  ▲                                                                       │
│  │ Populated by:                                                        │
│  └─── baselinr profile --config config.yml (with extract_lineage: true)│
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Lineage Collection (Offline)

```
CLI: baselinr profile
         │
         ▼
┌─────────────────────┐
│ Lineage Providers:  │
│  • dbt_manifest     │  → Reads manifest.json
│  • sql_parser       │  → Parses SQL/views
│  • query_history    │  → Queries warehouse logs
└─────────┬───────────┘
          │
          ▼
    Write to DB:
    baselinr_lineage table
    baselinr_column_lineage table
```

### 2. Dashboard Query Flow

```
User clicks "Lineage" in sidebar
         │
         ▼
Frontend: /app/lineage/page.tsx
         │
         ├─→ fetchLineageGraph()  ──HTTP──→  Backend: GET /api/lineage/graph
         │                                           │
         └─→ fetchLineageStats()  ──HTTP──→  Backend: GET /api/lineage/stats
                                                     │
                                                     ▼
                                           lineage_queries.py
                                                     │
                                                     ├─→ LineageQueryClient.get_all_lineage()
                                                     │
                                                     └─→ JOIN with runs/events for metrics
                                                          │
                                                          ▼
                                                    SQL Query to DB
                                                          │
                                                          ▼
                                                    Return JSON
         ◄───────────────────────────────────────────────┘
         │
         ▼
React Flow renders graph:
  • Nodes = tables
  • Edges = dependencies
  • Colors = drift status
```

### 3. Drift Investigation Flow

```
User sees drift alert
         │
         ▼
Clicks "Root Cause"
         │
         ▼
Frontend: DriftRootCausePanel
         │
         └─→ fetchDriftWithLineage(event_id) ──HTTP──→  Backend: GET /api/drift/{id}/lineage
                                                                │
                                                                ├─→ Fetch drift event
                                                                │
                                                                └─→ Get upstream lineage (2 hops)
                                                                     │
                                                                     ▼
                                                                Return drift + upstream tables
         ◄─────────────────────────────────────────────────────────┘
         │
         ▼
Display upstream tables to investigate
User clicks upstream table → Navigate to table detail page
```

## Component Hierarchy

### Frontend Component Tree

```
App
└── Layout
    ├── Sidebar (navigation)
    │
    └── Page Content
        │
        ├── /lineage
        │   └── LineagePage
        │       ├── LineageStats (KPIs)
        │       ├── LineageExplorer (filters)
        │       │   ├── SchemaFilter
        │       │   ├── ProviderFilter
        │       │   └── SearchBar
        │       └── LineageGraph (React Flow)
        │           ├── LineageNode (custom)
        │           └── LineageEdge (custom)
        │
        ├── /lineage/[tableName]
        │   └── TableLineagePage
        │       ├── TableHeader
        │       └── LineageGraph (focused on table)
        │
        ├── /tables/[tableName]
        │   └── TableDetailPage
        │       └── Tabs
        │           ├── Overview
        │           ├── Metrics
        │           └── Lineage (NEW)
        │               └── TableLineageView
        │                   ├── UpstreamList
        │                   └── DownstreamList
        │
        └── /drift
            └── DriftPage
                └── DriftAlertsTable
                    └── DriftAlert
                        └── DriftRootCausePanel (NEW)
                            ├── UpstreamTables
                            └── InvestigateButton
```

## Backend Architecture

### API Layer Structure

```
main.py (FastAPI app)
    │
    ├── /api/lineage/graph
    ├── /api/lineage/table/{name}
    ├── /api/lineage/path
    └── /api/lineage/stats
            │
            │ Calls
            ▼
lineage_queries.py
    │
    ├── get_lineage_graph()
    │       │
    │       ├─→ LineageQueryClient.get_all_lineage()
    │       │
    │       └─→ Enrich with profiling/drift data
    │           SELECT * FROM baselinr_runs WHERE ...
    │           SELECT * FROM baselinr_events WHERE ...
    │
    └── get_table_lineage()
            │
            ├─→ LineageQueryClient.get_upstream_tables()
            │
            └─→ LineageQueryClient.get_downstream_tables()
```

### Caching Strategy

```
API Request → Cache Check → Cache Hit? Yes → Return cached data
                    │              │
                    │              No
                    ▼              ▼
                Database Query → Store in cache (TTL: 5 min) → Return data
```

## Graph Visualization Architecture

### React Flow Integration

```
LineageGraph Component
    │
    ├── State Management
    │   ├── nodes: LineageNode[]
    │   ├── edges: LineageEdge[]
    │   ├── selectedNode: string | null
    │   └── filters: FilterState
    │
    ├── Data Processing
    │   ├── transformToReactFlowFormat()
    │   ├── applyFilters()
    │   └── calculateLayout()  (elkjs)
    │
    └── React Flow
        ├── <ReactFlow>
        │   ├── nodes={nodes}
        │   ├── edges={edges}
        │   └── nodeTypes={{ custom: LineageNode }}
        │
        ├── Controls (zoom, pan)
        ├── MiniMap
        └── Background
```

### Node Styling Logic

```typescript
function getNodeStyle(node: LineageNode) {
  // Border color based on drift status
  const borderColor = node.has_drift ? 'red' : 
                      node.has_profiling ? 'green' : 
                      'gray';
  
  // Background color based on node type
  const bgColor = node.node_type === 'source' ? '#e0f2fe' :
                  node.node_type === 'transform' ? '#fef3c7' :
                  '#f0fdf4';
  
  return { borderColor, bgColor };
}
```

### Edge Styling Logic

```typescript
function getEdgeStyle(edge: LineageEdge) {
  // Line style based on confidence
  const strokeWidth = edge.confidence_score > 0.9 ? 2 : 1;
  const strokeDasharray = edge.confidence_score < 0.8 ? '5,5' : undefined;
  
  // Color based on provider
  const stroke = edge.provider === 'dbt_manifest' ? '#0ea5e9' :
                 edge.provider.includes('query_history') ? '#8b5cf6' :
                 '#6b7280';
  
  // Opacity if stale
  const opacity = edge.is_stale ? 0.4 : 1.0;
  
  return { strokeWidth, strokeDasharray, stroke, opacity };
}
```

## Database Query Patterns

### Enriched Lineage Query

```sql
-- Get lineage with profiling/drift context
SELECT 
    l.upstream_schema,
    l.upstream_table,
    l.downstream_schema,
    l.downstream_table,
    l.provider,
    l.confidence_score,
    l.last_seen_at,
    r1.last_profiled_at as upstream_last_profiled,
    r2.last_profiled_at as downstream_last_profiled,
    COUNT(DISTINCT e1.event_id) as upstream_drift_count,
    COUNT(DISTINCT e2.event_id) as downstream_drift_count
FROM baselinr_lineage l
LEFT JOIN (
    SELECT dataset_name, schema_name, MAX(profiled_at) as last_profiled_at
    FROM baselinr_runs
    GROUP BY dataset_name, schema_name
) r1 ON l.upstream_table = r1.dataset_name 
    AND l.upstream_schema = r1.schema_name
LEFT JOIN (
    SELECT dataset_name, schema_name, MAX(profiled_at) as last_profiled_at
    FROM baselinr_runs
    GROUP BY dataset_name, schema_name
) r2 ON l.downstream_table = r2.dataset_name 
    AND l.downstream_schema = r2.schema_name
LEFT JOIN baselinr_events e1 
    ON l.upstream_table = e1.table_name 
    AND e1.drift_severity IN ('medium', 'high')
LEFT JOIN baselinr_events e2 
    ON l.downstream_table = e2.table_name 
    AND e2.drift_severity IN ('medium', 'high')
GROUP BY l.id
ORDER BY l.downstream_schema, l.downstream_table;
```

## Performance Considerations

### Backend Optimization

```
┌─────────────────────────┐
│ Request arrives         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Check Redis cache       │  ← 5 min TTL
└────────┬───────┬────────┘
         │       │
    Hit  │       │ Miss
         │       │
         ▼       ▼
    Return   Query DB
    Cached   ────┬────
    Data         │
                 ▼
           ┌─────────────┐
           │ Use indexes:│
           │ • (downstream)│
           │ • (upstream) │
           │ • (provider) │
           └──────┬──────┘
                  │
                  ▼
            Cache result
                  │
                  ▼
            Return data
```

### Frontend Optimization

```
Component Lifecycle:

1. Mount
   └─→ useQuery (React Query)
       └─→ Fetch data (cached for 5 min)

2. Render
   ├─→ useMemo: Transform data to React Flow format
   ├─→ useMemo: Apply filters
   └─→ useMemo: Calculate layout

3. User Interaction
   └─→ Debounce search input (300ms)
   └─→ Update filters (trigger re-render)

4. Large Graphs (>500 nodes)
   └─→ Enable virtualization
   └─→ Lazy load sections
   └─→ Show loading skeleton
```

## Security Considerations

```
Frontend                Backend                 Database
   │                       │                       │
   │  GET /api/lineage    │                       │
   ├──────────────────────>│                       │
   │                       │                       │
   │                       ├─ Validate auth       │
   │                       │  (if enabled)         │
   │                       │                       │
   │                       ├─ Sanitize params     │
   │                       │  (SQL injection)      │
   │                       │                       │
   │                       ├─ Apply row-level     │
   │                       │  security (if needed) │
   │                       │                       │
   │                       │  Query                │
   │                       ├──────────────────────>│
   │                       │                       │
   │                       │  Results              │
   │                       │<──────────────────────┤
   │                       │                       │
   │                       ├─ Filter sensitive    │
   │                       │  metadata             │
   │                       │                       │
   │  JSON Response        │                       │
   │<──────────────────────┤                       │
```

## Technology Stack

```
┌────────────────────────────────────────────┐
│ Frontend                                   │
│  • Next.js 14 (React framework)           │
│  • TypeScript                              │
│  • TailwindCSS (styling)                   │
│  • React Flow (graph visualization)        │
│  • React Query (data fetching/caching)     │
│  • Lucide React (icons)                    │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Backend                                    │
│  • FastAPI (Python web framework)          │
│  • Pydantic (data validation)              │
│  • SQLAlchemy (database ORM)               │
│  • Uvicorn (ASGI server)                   │
│  • baselinr.query.lineage_client           │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Database                                   │
│  • PostgreSQL / SQLite                     │
│  • Tables:                                 │
│    - baselinr_lineage                      │
│    - baselinr_column_lineage               │
│    - baselinr_runs                         │
│    - baselinr_events                       │
└────────────────────────────────────────────┘
```

## File Structure

```
workspace/
├── baselinr/
│   └── query/
│       └── lineage_client.py         ← Existing lineage query logic
│
├── dashboard/
│   ├── backend/
│   │   ├── main.py                   ← Add /api/lineage/* endpoints
│   │   ├── models.py                 ← Add Lineage* response models
│   │   ├── lineage_queries.py        ← NEW: Database query layer
│   │   └── database.py               ← Existing DB client
│   │
│   └── frontend/
│       ├── app/
│       │   ├── lineage/
│       │   │   ├── page.tsx          ← NEW: Main lineage page
│       │   │   └── [tableName]/
│       │   │       └── page.tsx      ← NEW: Table lineage detail
│       │   │
│       │   ├── tables/
│       │   │   └── [tableName]/
│       │   │       └── page.tsx      ← UPDATE: Add lineage tab
│       │   │
│       │   └── drift/
│       │       └── page.tsx          ← UPDATE: Add root cause
│       │
│       ├── components/
│       │   ├── LineageGraph.tsx      ← NEW: React Flow graph
│       │   ├── LineageStats.tsx      ← NEW: KPI cards
│       │   ├── LineageExplorer.tsx   ← NEW: Filters/search
│       │   ├── TableLineageView.tsx  ← NEW: Table lineage view
│       │   ├── DriftRootCausePanel.tsx ← NEW: Root cause panel
│       │   └── Sidebar.tsx           ← UPDATE: Add lineage nav
│       │
│       └── lib/
│           └── api.ts                ← UPDATE: Add lineage API calls
│
└── docs/
    └── dashboard/
        ├── LINEAGE_INTEGRATION_PLAN.md      ← Full plan
        ├── LINEAGE_IMPLEMENTATION_CHECKLIST.md ← Task list
        └── LINEAGE_ARCHITECTURE_DIAGRAM.md  ← This file
```

---

**Related Documentation**:
- [Full Integration Plan](./LINEAGE_INTEGRATION_PLAN.md)
- [Implementation Checklist](./LINEAGE_IMPLEMENTATION_CHECKLIST.md)
- [Data Lineage Guide](/docs/guides/DATA_LINEAGE.md)

**Last Updated**: 2025-11-27
