# ProfileMesh Dashboard v2.0

Internal dashboard MVP for ProfileMesh data profiling and drift detection. This dashboard visualizes profiling results, drift alerts, run history, and metrics across multi-warehouse environments.

## 🎯 Features

### Core Features
- **Run History**: View past profiling runs with filtering and search
- **Profiling Results**: Detailed table and column-level metrics visualization
- **Drift Detection**: Monitor data drift events with severity indicators
- **Metrics Dashboard**: Aggregate KPIs and trends
- **Multi-Warehouse Support**: PostgreSQL, Snowflake, MySQL, BigQuery, Redshift, SQLite
- **Export Functionality**: Export data in JSON/CSV formats

### Technical Stack

**Frontend**:
- Next.js 14 (App Router)
- React 18
- Tailwind CSS
- Recharts for visualizations
- TanStack Query for data fetching
- Lucide React for icons

**Backend**:
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL

## 📁 Project Structure

```
dashboard/
├── backend/                    # FastAPI backend
│   ├── main.py                # API endpoints
│   ├── models.py              # Pydantic models
│   ├── database.py            # Database client
│   ├── requirements.txt       # Python dependencies
│   └── sample_data_generator.py
├── frontend/                   # Next.js frontend
│   ├── app/                   # App router pages
│   │   ├── page.tsx           # Dashboard overview
│   │   ├── runs/              # Run history page
│   │   ├── drift/             # Drift alerts page
│   │   ├── tables/            # Table details page
│   │   └── metrics/           # Metrics page
│   ├── components/            # Reusable components
│   │   ├── Sidebar.tsx
│   │   ├── KPICard.tsx
│   │   ├── RunsTable.tsx
│   │   ├── DriftAlertsTable.tsx
│   │   └── FilterPanel.tsx
│   ├── lib/                   # Utilities
│   │   └── api.ts             # API client
│   └── package.json
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.10+
- PostgreSQL database (ProfileMesh storage)
- Existing ProfileMesh installation (Phase 1)

### 1. Backend Setup

```bash
cd dashboard/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
export PROFILEMESH_DB_URL=postgresql://profilemesh:profilemesh@localhost:5433/profilemesh
export API_HOST=0.0.0.0
export API_PORT=8000

# Generate sample data (optional)
python sample_data_generator.py

# Start the backend server
python main.py
# Or with uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### 2. Frontend Setup

```bash
cd dashboard/frontend

# Install dependencies
npm install
# or
yarn install

# Create .env.local file with:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Start the development server
npm run dev
# or
yarn dev
```

Frontend will be available at: `http://localhost:3000`

## 🔌 API Endpoints

### Dashboard Metrics
- `GET /api/dashboard/metrics?warehouse=&days=30` - Get aggregate metrics

### Run History
- `GET /api/runs?warehouse=&schema=&table=&status=&days=30` - List profiling runs
- `GET /api/runs/{run_id}` - Get detailed run results

### Drift Detection
- `GET /api/drift?warehouse=&table=&severity=&days=30` - List drift alerts

### Table Metrics
- `GET /api/tables/{table_name}/metrics?schema=&warehouse=` - Get table metrics

### Warehouses
- `GET /api/warehouses` - List available warehouses

### Export
- `GET /api/export/runs?format=json&warehouse=&days=30` - Export runs
- `GET /api/export/drift?format=json&warehouse=&days=30` - Export drift

## 📊 Sample Data

To populate the dashboard with sample data for testing:

```bash
cd dashboard/backend
python sample_data_generator.py
```

This generates:
- 100 profiling runs across all warehouse types
- Column-level metrics for each run
- Drift events for ~30% of runs

## 🎨 Customization

### Theme Colors

Modify `tailwind.config.ts` to customize colors:

```typescript
colors: {
  primary: {
    500: '#0ea5e9',  // Main brand color
    // ...
  },
}
```

### Adding New Pages

1. Create a new page in `frontend/app/your-page/page.tsx`
2. Add navigation link in `components/Sidebar.tsx`
3. Create API endpoint in `backend/main.py` if needed

## 🔗 Integration with ProfileMesh Phase 1

The dashboard connects to the ProfileMesh storage database to read:
- **profilemesh_runs**: Run history and metadata
- **profilemesh_results**: Column-level metrics
- **profilemesh_events**: Drift detection events
- **profilemesh_table_state**: Incremental profiling metadata (snapshot IDs, last decisions)

Ensure your ProfileMesh Phase 1 installation has created these tables.

## 🐳 Docker Setup (Optional)

TODO: Add Docker Compose configuration for easy deployment

## 📈 Roadmap / Future Enhancements

- [ ] Real-time updates via WebSockets
- [ ] Advanced filtering and saved views
- [ ] Custom dashboards per user
- [ ] Alert notifications (email, Slack)
- [ ] Figma-based design refinements
- [ ] CSV export implementation
- [ ] Pagination for large datasets
- [ ] Dark mode support
- [ ] User authentication

## 🤝 Contributing

This is an internal MVP. For feature requests or bug reports, please contact the ProfileMesh team.

## 📝 Environment Variables

### Backend (.env)
```
PROFILEMESH_DB_URL=postgresql://user:password@host:port/database
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

## 🛠️ Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm run dev
```

Visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📦 Production Build

### Frontend
```bash
cd frontend
npm run build
npm start
```

### Backend
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🐛 Troubleshooting

### Connection Errors
- Ensure ProfileMesh database is running
- Check `PROFILEMESH_DB_URL` environment variable
- Verify database tables exist (profilemesh_runs, profilemesh_results, profilemesh_events)

### No Data Showing
- Run the sample data generator: `python sample_data_generator.py`
- Or run ProfileMesh profiling: `profilemesh profile --config config.yml`

### CORS Errors
- Check `CORS_ORIGINS` in backend includes frontend URL
- Verify `NEXT_PUBLIC_API_URL` in frontend points to backend

## 📄 License

Internal use only - ProfileMesh Project

