# Lineage Integration Plan for Baselinr Dashboard

## Overview

This document outlines the plan for integrating data lineage visualization into the Baselinr dashboard. The lineage feature will enable users to visualize table and column-level dependencies, perform root cause analysis when drift is detected, and understand the impact of data changes across their warehouse.

## Current State

### Existing Infrastructure
- ✅ Lineage data collection via multiple providers (dbt, SQL parser, query history)
- ✅ Storage schema: `baselinr_lineage` and `baselinr_column_lineage` tables
- ✅ Query client: `baselinr/query/lineage_client.py` with comprehensive APIs
- ✅ CLI commands: `baselinr lineage upstream/downstream/path/sync`
- ✅ Dashboard infrastructure: FastAPI backend + Next.js frontend

### What's Missing
- ❌ Backend API endpoints for lineage data
- ❌ Frontend pages/components for lineage visualization
- ❌ Interactive lineage graph visualization
- ❌ Integration with drift alerts for root cause analysis
- ❌ Table detail pages showing lineage context

## Goals

### Primary Goals
1. **Visualize table-level lineage** as an interactive directed acyclic graph (DAG)
2. **Enable root cause analysis** by linking drift alerts to upstream lineage
3. **Provide impact analysis** by showing downstream dependencies
4. **Support exploration** with search, filtering, and drill-down capabilities

### Secondary Goals
1. **Column-level lineage** visualization (can be phased)
2. **Lineage health metrics** (staleness, confidence scores, provider coverage)
3. **Lineage path discovery** between any two tables
4. **Provider-specific filtering** (dbt vs query history vs SQL parser)

## Architecture

### Backend API Endpoints

Add the following endpoints to `dashboard/backend/main.py`:

#### 1. Get All Lineage Graph
```python
@app.get("/api/lineage/graph", response_model=LineageGraphResponse)
async def get_lineage_graph(
    schema: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    min_confidence: float = Query(0.0),
    include_stale: bool = Query(True)
)
```
Returns complete lineage graph for visualization, optionally filtered by schema/provider.

#### 2. Get Table Lineage
```python
@app.get("/api/lineage/table/{table_name}", response_model=TableLineageResponse)
async def get_table_lineage(
    table_name: str,
    schema: Optional[str] = Query(None),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    max_depth: int = Query(3),
    include_columns: bool = Query(False)
)
```
Returns upstream and/or downstream lineage for a specific table.

#### 3. Get Lineage Path
```python
@app.get("/api/lineage/path", response_model=LineagePathResponse)
async def get_lineage_path(
    from_table: str = Query(...),
    to_table: str = Query(...),
    from_schema: Optional[str] = Query(None),
    to_schema: Optional[str] = Query(None),
    max_depth: int = Query(5)
)
```
Finds path between two tables.

#### 4. Get Lineage Statistics
```python
@app.get("/api/lineage/stats", response_model=LineageStatsResponse)
async def get_lineage_stats(
    schema: Optional[str] = Query(None)
)
```
Returns metrics about lineage coverage: total edges, tables with lineage, provider breakdown, stale edges count.

#### 5. Get Column Lineage
```python
@app.get("/api/lineage/column/{table_name}/{column_name}", 
         response_model=ColumnLineageResponse)
async def get_column_lineage(
    table_name: str,
    column_name: str,
    schema: Optional[str] = Query(None),
    direction: str = Query("both"),
    max_depth: int = Query(3)
)
```
Returns column-level lineage for a specific column.

#### 6. Get Drift with Lineage Context
```python
@app.get("/api/drift/{event_id}/lineage", response_model=DriftLineageResponse)
async def get_drift_with_lineage(
    event_id: str,
    max_depth: int = Query(2)
)
```
Returns drift event with upstream lineage for root cause analysis.

### Backend Response Models

Add to `dashboard/backend/models.py`:

```python
class LineageNode(BaseModel):
    """A node in the lineage graph."""
    id: str  # schema.table format
    table_name: str
    schema_name: Optional[str]
    node_type: str  # 'source', 'transform', 'target'
    has_profiling: bool = False
    last_profiled: Optional[datetime] = None
    has_drift: bool = False
    drift_count: int = 0
    metadata: Dict[str, Any] = {}

class LineageEdge(BaseModel):
    """An edge in the lineage graph."""
    source: str  # node id (schema.table)
    target: str  # node id (schema.table)
    lineage_type: str  # 'dbt_ref', 'view', 'query', etc.
    provider: str  # 'dbt_manifest', 'sql_parser', 'postgres_query_history'
    confidence_score: float
    is_stale: bool = False
    last_seen_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class LineageGraphResponse(BaseModel):
    """Complete lineage graph."""
    nodes: List[LineageNode]
    edges: List[LineageEdge]
    stats: Dict[str, Any]

class TableLineageResponse(BaseModel):
    """Lineage for a specific table."""
    table_name: str
    schema_name: Optional[str]
    upstream: List[LineageNode]
    downstream: List[LineageNode]
    upstream_edges: List[LineageEdge]
    downstream_edges: List[LineageEdge]
    depth_reached: int
    total_upstream: int
    total_downstream: int

class LineagePathResponse(BaseModel):
    """Path between two tables."""
    path_found: bool
    path: List[LineageNode]
    edges: List[LineageEdge]
    path_length: int

class LineageStatsResponse(BaseModel):
    """Lineage health metrics."""
    total_tables: int
    tables_with_lineage: int
    total_edges: int
    stale_edges: int
    provider_breakdown: Dict[str, int]  # provider -> edge count
    coverage_percent: float
    avg_confidence_score: float

class ColumnLineageNode(BaseModel):
    """Column-level lineage node."""
    table_name: str
    schema_name: Optional[str]
    column_name: str
    column_type: Optional[str]
    depth: int

class ColumnLineageResponse(BaseModel):
    """Column-level lineage."""
    table_name: str
    column_name: str
    upstream: List[ColumnLineageNode]
    downstream: List[ColumnLineageNode]

class DriftLineageResponse(BaseModel):
    """Drift event with lineage context."""
    event: DriftAlertResponse
    upstream_lineage: List[LineageNode]
    upstream_edges: List[LineageEdge]
    affected_downstream: List[LineageNode]
```

### Backend Database Integration

Create `dashboard/backend/lineage_queries.py`:

```python
"""
Database queries for lineage data.
"""

class LineageQueries:
    """SQL queries for fetching lineage data."""
    
    def __init__(self, db_client: DatabaseClient):
        self.db_client = db_client
        # Use existing LineageQueryClient from baselinr
        from baselinr.query.lineage_client import LineageQueryClient
        self.lineage_client = LineageQueryClient(
            engine=db_client.engine,
            warn_stale_days=90
        )
    
    async def get_lineage_graph(self, schema, provider, min_confidence):
        """Get complete lineage graph with filters."""
        # Implementation using lineage_client
        pass
    
    async def get_table_with_metrics(self, table_name, schema):
        """Get table with profiling/drift metrics for enriched nodes."""
        # Join lineage with runs/events tables
        pass
    
    # ... other methods
```

### Frontend Structure

#### New Pages

1. **`/app/lineage/page.tsx`** - Main lineage visualization page
2. **`/app/lineage/[tableName]/page.tsx`** - Table-specific lineage detail
3. **`/app/tables/[tableName]/page.tsx`** - Enhanced with lineage tab (already exists)

#### New Components

1. **`/components/LineageGraph.tsx`**
   - Interactive DAG visualization using React Flow or D3.js
   - Node coloring based on drift status, profiling status
   - Edge styling based on provider, confidence, staleness
   - Zoom, pan, filter controls

2. **`/components/LineageExplorer.tsx`**
   - Search bar for finding tables
   - Filters: schema, provider, confidence threshold
   - Direction toggle (upstream/downstream/both)
   - Depth slider

3. **`/components/LineageStats.tsx`**
   - KPI cards for lineage health metrics
   - Provider breakdown chart
   - Staleness warnings

4. **`/components/LineagePathFinder.tsx`**
   - Input fields for source/target tables
   - Path visualization
   - "Show me path from X to Y" interface

5. **`/components/TableLineageView.tsx`**
   - Simplified lineage view for table detail pages
   - List view as alternative to graph
   - Upstream/downstream tabs

6. **`/components/DriftRootCausePanel.tsx`**
   - Shows drift alert with upstream context
   - "Investigate upstream" action
   - Suggested tables to check

#### Frontend API Client

Extend `/lib/api.ts`:

```typescript
export async function fetchLineageGraph(params?: {
  schema?: string;
  provider?: string;
  minConfidence?: number;
}) {
  const queryString = new URLSearchParams(params as any).toString();
  return fetch(`${API_URL}/api/lineage/graph?${queryString}`).then(r => r.json());
}

export async function fetchTableLineage(
  tableName: string,
  params?: {
    schema?: string;
    direction?: 'upstream' | 'downstream' | 'both';
    maxDepth?: number;
  }
) {
  const queryString = new URLSearchParams(params as any).toString();
  return fetch(`${API_URL}/api/lineage/table/${tableName}?${queryString}`).then(r => r.json());
}

export async function fetchLineagePath(
  fromTable: string,
  toTable: string,
  params?: {
    fromSchema?: string;
    toSchema?: string;
    maxDepth?: number;
  }
) {
  const queryString = new URLSearchParams({ from_table: fromTable, to_table: toTable, ...params } as any).toString();
  return fetch(`${API_URL}/api/lineage/path?${queryString}`).then(r => r.json());
}

export async function fetchLineageStats(schema?: string) {
  const queryString = schema ? `?schema=${schema}` : '';
  return fetch(`${API_URL}/api/lineage/stats${queryString}`).then(r => r.json());
}

export async function fetchDriftWithLineage(eventId: string, maxDepth?: number) {
  const queryString = maxDepth ? `?max_depth=${maxDepth}` : '';
  return fetch(`${API_URL}/api/drift/${eventId}/lineage${queryString}`).then(r => r.json());
}
```

## UI/UX Design

### Lineage Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Baselinr > Lineage                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Lineage Health Stats - KPI Cards]                        │
│  • Total Tables: 150   • With Lineage: 142 (94.6%)        │
│  • Total Edges: 387    • Stale Edges: 12 (3.1%)           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Filters: [Schema▼] [Provider▼] [Confidence≥0.8]          │
│  Search: [Find table...........................] 🔍        │
│  View:   ( ) Full Graph  (•) Focus Mode  ( ) List         │
│  Path:   From [table1] → To [table2] [Find Path]          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                  [Interactive Graph View]                   │
│                                                             │
│     ○ raw.events ──→ ○ staging.events_clean                │
│          │              │                                   │
│          ├──────────────┼──→ ○ analytics.revenue           │
│          │              └──→ ○ analytics.users             │
│          └──→ ⚠ raw.users                                  │
│                (has drift)                                  │
│                                                             │
│  Legend: ○ Profiled  ⚠ Has Drift  ◌ No Profiling         │
│          ──→ High Confidence  ··→ Low Confidence           │
│          dbt | query history | sql parser                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Table Detail Page - Lineage Tab

Add a new tab to existing `/app/tables/[tableName]/page.tsx`:

```
┌─────────────────────────────────────────────────────────────┐
│ Table: customers (public)                                   │
├─────────────────────────────────────────────────────────────┤
│ [Overview] [Metrics] [Lineage] [History]                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Upstream Dependencies (2)         Downstream Impact (5)    │
│ ┌───────────────────────┐         ┌──────────────────────┐│
│ │ ○ raw.users           │         │ ○ analytics.revenue  ││
│ │   via dbt_ref         │         │   2 tables depend on ││
│ │   confidence: 1.0     │         │   this table         ││
│ │                       │         │                      ││
│ │ ○ raw.events          │         │ ○ reports.monthly    ││
│ │   via query_history   │         │ ○ reports.weekly     ││
│ │   confidence: 0.95    │         │                      ││
│ └───────────────────────┘         └──────────────────────┘│
│                                                             │
│ [View Full Lineage Graph] [Find Path to...]               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Drift Alerts - Root Cause Analysis

Enhance `/app/drift/page.tsx` with lineage context:

```
┌─────────────────────────────────────────────────────────────┐
│ Drift Alert: customers - row_count                          │
├─────────────────────────────────────────────────────────────┤
│ Row count dropped 45% (10,000 → 5,500)                     │
│ Detected: 2025-11-27 10:23 AM                              │
│                                                             │
│ 🔍 Root Cause Analysis                                      │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Investigate upstream tables:                            ││
│ │ • raw.users (1 hop away)                               ││
│ │ • raw.events (1 hop away)                              ││
│ │                                                         ││
│ │ [View Lineage] [Check Upstream Drift]                  ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ Impact Analysis                                             │
│ • 3 downstream tables may be affected                      │
│ • analytics.revenue, reports.monthly, reports.weekly       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Navigation

Update `dashboard/frontend/components/Sidebar.tsx`:

```typescript
const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Runs', href: '/runs', icon: Activity },
  { name: 'Drift Detection', href: '/drift', icon: AlertTriangle },
  { name: 'Lineage', href: '/lineage', icon: GitBranch }, // NEW
  { name: 'Metrics', href: '/metrics', icon: BarChart3 },
]
```

## Implementation Phases

### Phase 1: Backend Foundation (Week 1)
**Goal**: Backend APIs ready for frontend consumption

- [ ] Add response models to `models.py`
- [ ] Create `lineage_queries.py` integrating with `LineageQueryClient`
- [ ] Implement 6 API endpoints in `main.py`
- [ ] Add tests for lineage endpoints
- [ ] Update API documentation

**Deliverable**: Backend API returning lineage data

### Phase 2: Basic Lineage Visualization (Week 2)
**Goal**: Users can view lineage graph

- [ ] Create `/app/lineage/page.tsx`
- [ ] Implement `LineageGraph.tsx` with React Flow
- [ ] Add `LineageStats.tsx` for health metrics
- [ ] Implement `LineageExplorer.tsx` for filters/search
- [ ] Update sidebar navigation
- [ ] Add API client functions to `lib/api.ts`

**Deliverable**: Basic lineage page with interactive graph

### Phase 3: Table Detail Integration (Week 3)
**Goal**: Lineage context in table views

- [ ] Create `/app/lineage/[tableName]/page.tsx`
- [ ] Add lineage tab to existing `/app/tables/[tableName]/page.tsx`
- [ ] Implement `TableLineageView.tsx`
- [ ] Add "View Lineage" links from Runs/Drift pages
- [ ] Implement breadcrumb navigation

**Deliverable**: Table-specific lineage views

### Phase 4: Drift Integration & Root Cause Analysis (Week 4)
**Goal**: Link drift alerts to lineage

- [ ] Implement `DriftRootCausePanel.tsx`
- [ ] Enhance drift alert detail page with upstream context
- [ ] Add "Investigate upstream" workflow
- [ ] Implement drift propagation visualization
- [ ] Add automated suggestions for root cause tables

**Deliverable**: Drift alerts with lineage context

### Phase 5: Advanced Features (Week 5-6)
**Goal**: Column lineage, path finding, advanced filters

- [ ] Implement `LineagePathFinder.tsx`
- [ ] Add column-level lineage visualization
- [ ] Implement provider-specific filtering/coloring
- [ ] Add lineage health dashboard
- [ ] Export lineage to various formats (SVG, JSON)
- [ ] Add lineage change tracking over time

**Deliverable**: Full-featured lineage experience

## Technical Considerations

### Graph Visualization Library

**Recommendation: React Flow**

Pros:
- Built for React, excellent TypeScript support
- Interactive by default (zoom, pan, drag)
- Customizable nodes/edges
- Performance with large graphs (virtualization)
- Good documentation

Alternatives:
- D3.js (more control, steeper learning curve)
- Cytoscape.js (specialized for DAGs)
- vis.js (simpler but less customizable)

### Performance Optimization

1. **Backend**:
   - Cache lineage graph queries (TTL: 5 minutes)
   - Use database indexes on lineage table (already exist)
   - Limit default max_depth to 3-5 hops
   - Implement pagination for large graphs

2. **Frontend**:
   - Lazy load graph data
   - Virtualize large node lists
   - Debounce search/filter inputs
   - Use React Query for caching

3. **Database**:
   - Existing indexes should be sufficient
   - Consider materialized views for complex joins with runs/drift tables
   - Monitor query performance

### Scalability

For large warehouses (1000+ tables):
- Implement graph clustering/grouping by schema
- Add "focus mode" to show only N hops from selected table
- Provide list view as alternative to graph
- Consider server-side graph layout computation

### Data Freshness

- Display "last synced" timestamp for query history lineage
- Show staleness warnings prominently
- Provide "Refresh lineage" action
- Link to CLI docs for `baselinr lineage sync`

## Testing Strategy

### Backend Tests
- Unit tests for each API endpoint
- Test lineage query logic with sample data
- Test edge cases (cycles, disconnected components, missing schemas)
- Performance tests with large graphs

### Frontend Tests
- Component tests for graph rendering
- Integration tests for filters/search
- E2E tests for user workflows
- Visual regression tests for graph layouts

### User Acceptance Testing
- Test with real user data (anonymized)
- Validate use cases: drift investigation, impact analysis
- Performance testing with production-scale data
- Gather feedback on UX/navigation

## Documentation

### User Documentation
- [ ] Create `/docs/dashboard/LINEAGE_GUIDE.md`
- [ ] Add lineage section to `/docs/dashboard/QUICKSTART.md`
- [ ] Update screenshots in README
- [ ] Create video walkthrough

### Developer Documentation
- [ ] Document API endpoints in OpenAPI/Swagger
- [ ] Add architecture diagram
- [ ] Document graph visualization component API
- [ ] Add contribution guide for lineage providers

## Success Metrics

### Adoption Metrics
- % of users who visit lineage page (target: >60%)
- Average time spent on lineage page
- % of drift investigations that use lineage (target: >40%)

### Technical Metrics
- Page load time <2s for graphs with <500 nodes
- API response time <500ms for lineage queries
- Zero critical bugs in first month
- Test coverage >80%

### User Satisfaction
- User feedback/surveys (target: >4/5 rating)
- Feature requests related to lineage
- Support tickets about lineage (lower is better)

## Dependencies

### Backend Dependencies
- Existing: FastAPI, SQLAlchemy, Pydantic
- New: None (leverage existing lineage_client)

### Frontend Dependencies
- Existing: Next.js, React, TailwindCSS, React Query
- New:
  - `reactflow` (^11.10.0) - Graph visualization
  - `lucide-react` (already installed) - Icons
  - Optional: `elkjs` (graph layout algorithms)

### Installation
```bash
cd dashboard/frontend
npm install reactflow
```

## Migration & Rollout

### Rollout Strategy
1. Deploy backend APIs first (backward compatible)
2. Deploy frontend with feature flag
3. Beta test with internal users
4. Gradual rollout to all users
5. Monitor metrics, gather feedback

### Feature Flag
Add to config:
```yaml
dashboard:
  features:
    lineage: true  # Enable lineage page
    lineage_beta: false  # Beta features (column lineage, etc.)
```

### Backward Compatibility
- All new endpoints are additive (no breaking changes)
- Frontend gracefully handles missing lineage data
- Works with existing database schema (no migrations needed)

## Future Enhancements

### Post-Launch Ideas
1. **Column-level lineage graph** - Visualize column dependencies
2. **Lineage diffs** - Show lineage changes over time
3. **Impact simulation** - "What if I change this table?"
4. **Lineage-aware alerts** - Group alerts by root cause
5. **AI-powered root cause** - LLM suggests likely causes based on lineage
6. **Lineage export** - Download graph as SVG, PNG, or DOT format
7. **Collaborative features** - Annotations, comments on lineage
8. **Lineage quality score** - Measure completeness/accuracy
9. **Integration with dbt docs** - Link to dbt documentation
10. **Real-time lineage updates** - WebSocket-based live updates

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Graph too complex for large warehouses | High | Implement clustering, focus mode, list view |
| Poor performance with 1000+ tables | High | Caching, pagination, optimize queries |
| Users don't understand lineage | Medium | Tooltips, help text, onboarding tour |
| Stale lineage data misleads users | High | Prominent staleness warnings, refresh actions |
| Browser memory issues with large graphs | Medium | Virtualization, lazy loading |
| Column lineage too slow | Low | Phase it separately, optimize or defer |

## Appendix

### Example Lineage Queries

```python
# Get upstream tables
upstream = lineage_client.get_upstream_tables(
    table_name="customers",
    schema_name="public",
    max_depth=3
)

# Get downstream tables
downstream = lineage_client.get_downstream_tables(
    table_name="raw_events",
    schema_name="raw",
    max_depth=2
)

# Find path
path = lineage_client.get_lineage_path(
    from_table="raw_events",
    to_table="revenue",
    from_schema="raw",
    to_schema="analytics",
    max_depth=5
)

# Get all lineage
all_lineage = lineage_client.get_all_lineage()
```

### Example API Responses

```json
// GET /api/lineage/graph
{
  "nodes": [
    {
      "id": "public.customers",
      "table_name": "customers",
      "schema_name": "public",
      "node_type": "transform",
      "has_profiling": true,
      "last_profiled": "2025-11-27T10:00:00Z",
      "has_drift": false,
      "drift_count": 0
    }
  ],
  "edges": [
    {
      "source": "raw.users",
      "target": "public.customers",
      "lineage_type": "dbt_ref",
      "provider": "dbt_manifest",
      "confidence_score": 1.0,
      "is_stale": false,
      "last_seen_at": "2025-11-27T09:00:00Z"
    }
  ],
  "stats": {
    "total_nodes": 42,
    "total_edges": 87,
    "providers": ["dbt_manifest", "postgres_query_history"]
  }
}
```

## References

- [Data Lineage Guide](/docs/guides/DATA_LINEAGE.md)
- [Dashboard Architecture](/docs/dashboard/ARCHITECTURE.md)
- [React Flow Documentation](https://reactflow.dev/)
- [Lineage Query Client](/baselinr/query/lineage_client.py)

---

**Status**: 📋 Proposed  
**Owner**: TBD  
**Target Completion**: 6 weeks from start  
**Last Updated**: 2025-11-27
