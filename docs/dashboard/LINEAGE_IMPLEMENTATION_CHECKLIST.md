# Lineage Dashboard Implementation Checklist

Quick reference checklist for implementing lineage visualization in the Baselinr dashboard.

## 🎯 Quick Summary

Add data lineage visualization to the dashboard to enable:
- Interactive graph showing table dependencies
- Root cause analysis when drift is detected
- Impact analysis for data changes
- Path finding between tables

**Estimated Timeline**: 4-6 weeks  
**Team Size**: 1-2 developers

---

## Phase 1: Backend Foundation ⚙️

### 1.1 Response Models (`dashboard/backend/models.py`)

```python
# Add these new models:
- [ ] LineageNode
- [ ] LineageEdge
- [ ] LineageGraphResponse
- [ ] TableLineageResponse
- [ ] LineagePathResponse
- [ ] LineageStatsResponse
- [ ] ColumnLineageResponse
- [ ] DriftLineageResponse
```

### 1.2 Database Integration (`dashboard/backend/lineage_queries.py`)

```python
# Create new file with LineageQueries class
- [ ] Import LineageQueryClient from baselinr.query.lineage_client
- [ ] Implement get_lineage_graph()
- [ ] Implement get_table_lineage()
- [ ] Implement get_lineage_path()
- [ ] Implement get_lineage_stats()
- [ ] Implement enrich_nodes_with_metrics() (join with runs/drift tables)
- [ ] Add caching decorator (5 min TTL)
```

### 1.3 API Endpoints (`dashboard/backend/main.py`)

```python
- [ ] GET /api/lineage/graph
- [ ] GET /api/lineage/table/{table_name}
- [ ] GET /api/lineage/path
- [ ] GET /api/lineage/stats
- [ ] GET /api/lineage/column/{table_name}/{column_name}
- [ ] GET /api/drift/{event_id}/lineage
```

### 1.4 Testing & Documentation

```bash
- [ ] Write unit tests for all endpoints
- [ ] Test with sample lineage data
- [ ] Update API docs/Swagger
- [ ] Test performance with large graphs (>500 nodes)
```

**Checkpoint**: Backend APIs return lineage data via HTTP

---

## Phase 2: Basic Lineage Visualization 📊

### 2.1 Install Dependencies

```bash
cd dashboard/frontend
npm install reactflow
```

### 2.2 API Client (`dashboard/frontend/lib/api.ts`)

```typescript
- [ ] fetchLineageGraph()
- [ ] fetchTableLineage()
- [ ] fetchLineagePath()
- [ ] fetchLineageStats()
- [ ] fetchColumnLineage()
- [ ] fetchDriftWithLineage()
```

### 2.3 Components

```typescript
// dashboard/frontend/components/
- [ ] LineageGraph.tsx (React Flow graph)
- [ ] LineageStats.tsx (KPI cards)
- [ ] LineageExplorer.tsx (filters/search)
- [ ] LineageNode.tsx (custom node component)
- [ ] LineageEdge.tsx (custom edge component)
```

### 2.4 Main Lineage Page (`dashboard/frontend/app/lineage/page.tsx`)

```typescript
- [ ] Create page layout
- [ ] Add stats section at top
- [ ] Add filter/search controls
- [ ] Integrate LineageGraph component
- [ ] Add loading/error states
- [ ] Add empty state (no lineage data)
```

### 2.5 Navigation (`dashboard/frontend/components/Sidebar.tsx`)

```typescript
- [ ] Add "Lineage" menu item with GitBranch icon
- [ ] Update navigation array
- [ ] Test active state highlighting
```

**Checkpoint**: Users can view lineage graph at `/lineage`

---

## Phase 3: Table Detail Integration 🔗

### 3.1 Table-Specific Lineage Page

```typescript
// dashboard/frontend/app/lineage/[tableName]/page.tsx
- [ ] Create dynamic route
- [ ] Fetch table lineage data
- [ ] Show focused graph (only this table + neighbors)
- [ ] Add upstream/downstream sections
- [ ] Add breadcrumb navigation
```

### 3.2 Enhance Existing Table Page

```typescript
// dashboard/frontend/app/tables/[tableName]/page.tsx
- [ ] Add "Lineage" tab to existing tabs
- [ ] Create TableLineageView component
- [ ] Show upstream dependencies list
- [ ] Show downstream impact list
- [ ] Add "View Full Lineage" button
```

### 3.3 Cross-linking

```typescript
- [ ] Add lineage icon/link in RunsTable
- [ ] Add lineage icon/link in DriftAlertsTable
- [ ] Add "View Lineage" button in table metrics page
- [ ] Add breadcrumb navigation between pages
```

**Checkpoint**: Lineage is accessible from table views

---

## Phase 4: Drift Integration 🔍

### 4.1 Root Cause Panel Component

```typescript
// dashboard/frontend/components/DriftRootCausePanel.tsx
- [ ] Accept drift event prop
- [ ] Fetch upstream lineage
- [ ] Display upstream tables list
- [ ] Add "Investigate upstream" button
- [ ] Show confidence scores
- [ ] Add "Check drift in upstream" action
```

### 4.2 Enhance Drift Alert Page

```typescript
// dashboard/frontend/app/drift/page.tsx
- [ ] Add lineage column to drift table
- [ ] Add "Root Cause" action button
- [ ] Create drift detail modal/page
- [ ] Integrate DriftRootCausePanel
- [ ] Add "View Lineage Graph" button
```

### 4.3 Drift Detail Page (Optional)

```typescript
// dashboard/frontend/app/drift/[eventId]/page.tsx
- [ ] Create new detail page
- [ ] Show drift metrics
- [ ] Show DriftRootCausePanel
- [ ] Show mini lineage graph
- [ ] Link to upstream table details
```

**Checkpoint**: Drift alerts have lineage context

---

## Phase 5: Polish & Advanced Features ✨

### 5.1 Path Finder

```typescript
// dashboard/frontend/components/LineagePathFinder.tsx
- [ ] Two input fields (from/to tables)
- [ ] Autocomplete for table names
- [ ] "Find Path" button
- [ ] Render path result
- [ ] Highlight path in main graph
```

### 5.2 Column Lineage (Optional)

```typescript
// dashboard/frontend/app/lineage/column/page.tsx
- [ ] Column lineage graph
- [ ] Column search/filter
- [ ] Show transformations
- [ ] Link to table lineage
```

### 5.3 Advanced Filters

```typescript
- [ ] Schema filter dropdown
- [ ] Provider filter (dbt, query history, etc.)
- [ ] Confidence threshold slider
- [ ] Date range filter
- [ ] "Show only stale" toggle
```

### 5.4 Graph Customization

```typescript
- [ ] Node coloring by drift status
- [ ] Edge styling by provider
- [ ] Layout algorithm selection
- [ ] Export graph (SVG, PNG)
- [ ] Minimap for large graphs
```

### 5.5 Performance Optimization

```typescript
- [ ] Implement graph clustering for large warehouses
- [ ] Add virtualization for node lists
- [ ] Lazy load graph sections
- [ ] Debounce search/filter
- [ ] Add loading skeletons
```

**Checkpoint**: Feature complete!

---

## Testing Checklist ✅

### Backend Tests

```bash
- [ ] Test all API endpoints return 200
- [ ] Test with empty lineage data
- [ ] Test with cyclic dependencies
- [ ] Test with large graphs (1000+ nodes)
- [ ] Test caching behavior
- [ ] Test error handling
- [ ] Test query performance (<500ms)
```

### Frontend Tests

```bash
- [ ] Component unit tests (Jest/React Testing Library)
- [ ] Graph rendering tests
- [ ] Filter/search functionality
- [ ] Navigation tests
- [ ] E2E tests (Playwright/Cypress)
- [ ] Visual regression tests
- [ ] Mobile responsiveness
```

### User Acceptance Testing

```bash
- [ ] Test with real user data
- [ ] Validate drift investigation workflow
- [ ] Test impact analysis use case
- [ ] Gather feedback on UX
- [ ] Test with different browsers
- [ ] Test with different screen sizes
```

---

## Documentation Checklist 📚

### User Documentation

```markdown
- [ ] Create /docs/dashboard/LINEAGE_GUIDE.md
- [ ] Update /docs/dashboard/QUICKSTART.md
- [ ] Add screenshots to README
- [ ] Create video walkthrough
- [ ] Add tooltips in UI
- [ ] Create onboarding tour
```

### Developer Documentation

```markdown
- [ ] Document API endpoints (Swagger)
- [ ] Add architecture diagram
- [ ] Document graph component props
- [ ] Add code examples
- [ ] Update CONTRIBUTING.md
```

---

## Deployment Checklist 🚀

### Pre-Deployment

```bash
- [ ] Run all tests
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Review security (no sensitive data exposed)
- [ ] Test with production data (anonymized)
- [ ] Performance test with load
```

### Deployment

```bash
- [ ] Deploy backend first
- [ ] Verify backend health
- [ ] Deploy frontend
- [ ] Verify frontend health
- [ ] Run smoke tests
- [ ] Monitor error logs
```

### Post-Deployment

```bash
- [ ] Announce new feature to users
- [ ] Monitor usage metrics
- [ ] Gather user feedback
- [ ] Track performance metrics
- [ ] Address bug reports
- [ ] Plan next iteration
```

---

## Quick Commands Reference

### Backend Development

```bash
# Run backend locally
cd dashboard/backend
python main.py

# Run tests
pytest test_lineage_api.py -v

# Check API docs
open http://localhost:8000/docs
```

### Frontend Development

```bash
# Run frontend locally
cd dashboard/frontend
npm run dev

# Run tests
npm test

# Build production
npm run build
```

### Test Full Stack

```bash
# Start both backend and frontend
baselinr ui --config examples/config.yml

# Access dashboard
open http://localhost:3000
```

---

## Key Files Reference

| Component | File Path |
|-----------|-----------|
| Backend API | `dashboard/backend/main.py` |
| Response Models | `dashboard/backend/models.py` |
| Lineage Queries | `dashboard/backend/lineage_queries.py` |
| Lineage Client (existing) | `baselinr/query/lineage_client.py` |
| Frontend Lineage Page | `dashboard/frontend/app/lineage/page.tsx` |
| Graph Component | `dashboard/frontend/components/LineageGraph.tsx` |
| API Client | `dashboard/frontend/lib/api.ts` |
| Sidebar Nav | `dashboard/frontend/components/Sidebar.tsx` |
| Database Schema | `baselinr/storage/schema.sql` (tables already exist) |

---

## Success Criteria

- ✅ Users can view lineage graph for their warehouse
- ✅ Users can investigate drift using upstream lineage
- ✅ Users can find paths between tables
- ✅ Page load time <2s for typical graphs
- ✅ API response time <500ms
- ✅ Test coverage >80%
- ✅ Zero P0/P1 bugs in first week
- ✅ Positive user feedback (>4/5 rating)

---

## Need Help?

- 📖 Full plan: [LINEAGE_INTEGRATION_PLAN.md](./LINEAGE_INTEGRATION_PLAN.md)
- 🔧 Lineage guide: [/docs/guides/DATA_LINEAGE.md](/docs/guides/DATA_LINEAGE.md)
- 🏗️ Dashboard architecture: [/docs/dashboard/ARCHITECTURE.md](/docs/dashboard/ARCHITECTURE.md)
- 💬 Questions: Open an issue on GitHub

---

**Last Updated**: 2025-11-27  
**Status**: Ready to implement
