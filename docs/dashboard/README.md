# Baselinr Quality Studio

Quality Studio is Baselinr's no-code web interface for configuring and managing your entire data quality setup. Configure connections, tables, profiling settings, validation rules, drift detection, and more—all through an intuitive visual interface. The Quality Studio also provides comprehensive monitoring and analysis of profiling results, drift alerts, run history, and metrics across multi-warehouse environments.

## 📚 Demo Documentation

The Quality Studio supports a **demo mode** that runs entirely on Cloudflare Pages without database dependencies:

- **[Demo Documentation Hub](DEMO.md)** - Complete demo deployment guide
- **[Demo Mode Quick Start](DEMO_MODE.md)** - Enable demo mode locally
- **[Demo Deployment Guide](DEMO_DEPLOYMENT.md)** - Phased deployment approach

## 🎮 Try the Demo

**👉 [Try Quality Studio Demo →](https://demo.baselinr.io)**

Experience the Quality Studio with realistic sample data. The demo showcases all features including:
- Configuration management
- Profiling results visualization
- Drift detection alerts
- Validation results
- Root cause analysis
- Metrics dashboards

*Note: The demo uses pre-generated sample data and runs in read-only mode.*

## 🎯 Features

### Core Features
- **No-Code Configuration**: Set up your entire data quality configuration through visual forms—no YAML or JSON required
- **Configuration Management**: Visual editors for connections, storage, tables, profiling, validation rules, drift detection, and more
- **Visual & YAML Editor**: Split-view editor with real-time sync between visual forms and YAML configuration
- **Run History**: View past profiling runs with filtering and search
- **Profiling Results**: Detailed table and column-level metrics visualization
- **Drift Detection**: Monitor data drift events with severity indicators
- **Validation Results**: View and manage data quality validation results
- **Root Cause Analysis**: AI-powered correlation of anomalies with pipeline runs and upstream issues
- **Metrics Overview**: Aggregate KPIs and trends
- **Multi-Warehouse Support**: PostgreSQL, Snowflake, MySQL, BigQuery, Redshift, SQLite
- **Export Functionality**: Export data in JSON/CSV formats
- **AI Chat Assistant**: Conversational interface for data quality investigation

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
│   ├── chat_models.py         # Chat API models
│   ├── chat_routes.py         # Chat API routes
│   ├── requirements.txt       # Python dependencies
│   └── sample_data_generator.py
├── frontend/                   # Next.js frontend
│   ├── app/                   # App router pages
│   │   ├── page.tsx           # Quality Studio overview
│   │   ├── runs/              # Run history page
│   │   ├── drift/             # Drift alerts page
│   │   ├── tables/            # Table details page
│   │   ├── chat/              # AI Chat page
│   │   └── metrics/           # Metrics page
│   ├── components/            # Reusable components
│   │   ├── Sidebar.tsx
│   │   ├── KPICard.tsx
│   │   ├── RunsTable.tsx
│   │   ├── DriftAlertsTable.tsx
│   │   ├── FilterPanel.tsx
│   │   └── chat/             # Chat components
│   │       ├── ChatContainer.tsx
│   │       ├── ChatInput.tsx
│   │       └── ChatMessage.tsx
│   ├── types/                 # TypeScript types
│   │   ├── lineage.ts
│   │   └── chat.ts
│   ├── lib/                   # Utilities
│   │   └── api.ts             # API client
│   └── package.json
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.10+
- PostgreSQL database (Baselinr storage)
- Existing Baselinr installation (Phase 1)

### 1. Backend Setup

```bash
cd dashboard/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
export BASELINR_DB_URL=postgresql://baselinr:baselinr@localhost:5433/baselinr
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

### Quality Studio Metrics
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

### Chat (AI Assistant)
- `GET /api/chat/config` - Get chat configuration status
- `POST /api/chat/message` - Send a message to the chat agent
- `GET /api/chat/history/{session_id}` - Get chat history for a session
- `DELETE /api/chat/session/{session_id}` - Clear a chat session
- `GET /api/chat/tools` - List available chat tools
- `GET /api/chat/sessions` - List active chat sessions

## 📊 Sample Data

To populate the Quality Studio with sample data for testing:

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

## 🔗 Integration with Baselinr Phase 1

The dashboard connects to the Baselinr storage database to read:
- **baselinr_runs**: Run history and metadata
- **baselinr_results**: Column-level metrics
- **baselinr_events**: Drift detection events
- **baselinr_table_state**: Incremental profiling metadata (snapshot IDs, last decisions)

Ensure your Baselinr Phase 1 installation has created these tables.

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

This is an internal MVP. For feature requests or bug reports, please contact the Baselinr team.

## 📝 Environment Variables

### Backend (.env)
```
BASELINR_DB_URL=postgresql://user:password@host:port/database
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Chat/AI Configuration (optional)
LLM_ENABLED=true
LLM_PROVIDER=openai  # or "anthropic"
LLM_MODEL=gpt-4o-mini  # or "claude-3-5-sonnet-20241022"
OPENAI_API_KEY=sk-your-api-key
# ANTHROPIC_API_KEY=sk-ant-your-api-key  # if using Anthropic
CHAT_MAX_ITERATIONS=5
CHAT_MAX_HISTORY=20
CHAT_TOOL_TIMEOUT=30

# Or use a config file
BASELINR_CONFIG=/path/to/config.yml
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

## 💬 Chat Feature

The Quality Studio includes an AI-powered chat assistant for data quality investigation.

### Enabling Chat

1. Set `LLM_ENABLED=true` in your environment
2. Configure your LLM provider (OpenAI or Anthropic)
3. Provide the appropriate API key

### Chat Capabilities

The chat assistant can:
- Query recent profiling runs
- Investigate drift events and anomalies
- Get table profiles and column statistics
- Compare runs and analyze trends
- Explore data lineage relationships
- Search across tables

### Example Queries

- "What tables have been profiled recently?"
- "Show me high severity drift events"
- "Are there any anomalies I should investigate?"
- "Compare the last two runs for the customers table"
- "What's the trend for null rate in the email column?"
- "What are the upstream sources for orders table?"

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
- Ensure Baselinr database is running
- Check `BASELINR_DB_URL` environment variable
- Verify database tables exist (baselinr_runs, baselinr_results, baselinr_events)

### No Data Showing
- Run the sample data generator: `python sample_data_generator.py`
- Or run Baselinr profiling: `baselinr profile --config config.yml`

### CORS Errors
- Check `CORS_ORIGINS` in backend includes frontend URL
- Verify `NEXT_PUBLIC_API_URL` in frontend points to backend

## 📄 License

Internal use only - Baselinr Project

