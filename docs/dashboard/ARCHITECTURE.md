# Baselinr Quality Studio Architecture

## Overview

The Baselinr Quality Studio is a full-stack web application that provides no-code configuration management, visualization, and monitoring capabilities for the Baselinr data profiling system.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Next.js Frontend (Port 3000)                         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│  │  │Overview  │ │   Runs   │ │  Drift   │  Pages       │  │
│  │  └──────────┘ └──────────┘ └──────────┘              │  │
│  │  ┌──────────────────────────────────────┐             │  │
│  │  │  React Query (State & Caching)       │             │  │
│  │  └──────────────────────────────────────┘             │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 FastAPI Backend (Port 8000)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoints                                       │   │
│  │  /api/runs, /api/drift, /api/dashboard/metrics      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Database Client (SQLAlchemy)                        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL Queries
                         │
┌────────────────────────▼────────────────────────────────────┐
│              PostgreSQL Database (Port 5433)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Baselinr Storage                                 │   │
│  │  • baselinr_runs                                  │   │
│  │  • baselinr_results                               │   │
│  │  • baselinr_events                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         ▲
                         │ Writes
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Baselinr Core (Phase 1)                     │
│  • Profiling Engine                                         │
│  • Drift Detector                                           │
│  • Storage Writer                                           │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI Library**: React 18
- **Styling**: Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **Charts**: Recharts
- **Icons**: Lucide React
- **HTTP Client**: Fetch API
- **Type Safety**: TypeScript

### Backend
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Server**: Uvicorn
- **Database**: PostgreSQL

## Component Architecture

### Frontend Components

```
app/
├── layout.tsx                 # Root layout with sidebar
├── providers.tsx              # React Query provider setup
├── page.tsx                   # Dashboard overview page
├── runs/page.tsx              # Run history page
├── drift/page.tsx             # Drift detection page
├── tables/[tableName]/page.tsx # Dynamic table details
└── metrics/page.tsx           # Metrics & analytics page

components/
├── Sidebar.tsx                # Navigation sidebar
├── KPICard.tsx                # Key metric display
├── RunsTable.tsx              # Runs data table
├── DriftAlertsTable.tsx       # Drift alerts table
└── FilterPanel.tsx            # Filter controls

lib/
└── api.ts                     # API client functions
```

### Backend Components

```
backend/
├── main.py                    # FastAPI app & endpoints
├── models.py                  # Pydantic models
├── database.py                # Database client
└── sample_data_generator.py   # Test data generator
```

## Data Flow

### 1. Profiling Run Flow
```
Baselinr CLI
    ↓ (profiles data)
Profiling Engine
    ↓ (writes results)
PostgreSQL Database
    ↑ (queries data)
FastAPI Backend
    ↑ (REST API)
Next.js Frontend
    ↑ (displays)
User Browser
```

### 2. Dashboard Page Load
```
1. User visits /
2. Next.js renders page.tsx
3. React Query fetches /api/dashboard/metrics
4. FastAPI queries database
5. Returns aggregate metrics
6. React Query caches response
7. Page displays KPIs, charts, recent runs
```

### 3. Filtering Flow
```
1. User adjusts filters in FilterPanel
2. State updates trigger React Query refetch
3. API called with query parameters
4. Backend applies WHERE clauses
5. Filtered results returned
6. UI updates with new data
```

## Database Schema

### baselinr_runs
Stores metadata about each profiling run.

```sql
- run_id (PK)
- dataset_name
- schema_name
- profiled_at
- environment
- row_count
- column_count
- status
```

### baselinr_results
Stores column-level metrics.

```sql
- run_id (FK)
- column_name
- column_type
- metric_name
- metric_value
```

### baselinr_events
Stores drift detection events.

```sql
- event_id (PK)
- run_id (FK)
- event_type
- table_name
- column_name
- metric_name
- baseline_value
- current_value
- change_percent
- drift_severity
- timestamp
```

## API Design

### RESTful Endpoints

All endpoints follow REST conventions:
- `GET /api/resource` - List resources
- `GET /api/resource/{id}` - Get specific resource
- Query parameters for filtering

### Response Format
```json
{
  "run_id": "run_abc123",
  "dataset_name": "customers",
  "profiled_at": "2024-01-15T10:30:00Z",
  "row_count": 10000,
  ...
}
```

### Error Handling
```json
{
  "detail": "Run abc123 not found"
}
```

## State Management

### React Query
- Caches API responses
- Automatic background refetching
- Optimistic updates
- Loading/error states

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['runs', filters],
  queryFn: () => fetchRuns(filters),
})
```

## Performance Considerations

### Frontend
- React Query caching (1 minute stale time)
- Code splitting with Next.js
- Optimized images
- Lazy loading for large tables

### Backend
- Database connection pooling
- Query optimization with indexes
- Pagination for large datasets
- Async/await for non-blocking I/O

### Database
- Indexes on frequently queried columns
  - `baselinr_runs.dataset_name`
  - `baselinr_runs.profiled_at`
  - `baselinr_events.run_id`

## Security

### Current (MVP)
- CORS configuration
- No authentication (internal use only)
- Database connection string in environment variables

### Future Enhancements
- [ ] User authentication (OAuth2/JWT)
- [ ] Role-based access control
- [ ] API rate limiting
- [ ] Input sanitization
- [ ] SQL injection prevention (using SQLAlchemy parameterized queries)

## Deployment

### Development
```bash
# Backend
uvicorn main:app --reload

# Frontend
npm run dev
```

### Production
```bash
# Backend
uvicorn main:app --workers 4

# Frontend
npm run build && npm start
```

### Docker (Future)
```yaml
services:
  dashboard-backend:
    build: ./backend
    ports: ["8000:8000"]
  
  dashboard-frontend:
    build: ./frontend
    ports: ["3000:3000"]
```

## Monitoring & Logging

### Backend
- FastAPI automatic request logging
- Error tracebacks
- Database query logging (SQLAlchemy)

### Frontend
- Console errors in development
- React Query DevTools
- Network tab monitoring

## Extensibility

### Adding New Visualizations
1. Create chart component
2. Add to relevant page
3. Fetch data via React Query

### Adding New API Endpoints
1. Define Pydantic model in `models.py`
2. Add database query in `database.py`
3. Create endpoint in `main.py`
4. Add API function in frontend `lib/api.ts`

### Adding New Pages
1. Create `app/new-page/page.tsx`
2. Add route to `Sidebar.tsx`
3. Implement page logic

## Testing Strategy (Future)

### Backend
- Unit tests with pytest
- API endpoint tests
- Database query tests

### Frontend
- Component tests with Jest
- Integration tests with React Testing Library
- E2E tests with Playwright

## Roadmap

### Phase 2.1 - Enhanced Features
- [ ] Real-time updates (WebSockets)
- [ ] Advanced filtering
- [ ] Custom dashboards
- [ ] Alert notifications

### Phase 2.2 - Production Ready
- [ ] User authentication
- [ ] Docker deployment
- [ ] CI/CD pipeline
- [ ] Monitoring & alerting

### Phase 2.3 - Advanced
- [ ] Machine learning insights
- [ ] Anomaly detection
- [ ] Predictive analytics
- [ ] Multi-tenant support

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

