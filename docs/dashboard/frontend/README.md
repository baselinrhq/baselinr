# Baselinr Dashboard Frontend

Next.js 14 frontend application for the Baselinr internal dashboard.

## Features

- Modern React with Next.js App Router
- Tailwind CSS for styling
- Recharts for data visualization
- TanStack Query for server state management
- Responsive design
- Filter and export functionality

## Installation

```bash
npm install
# or
yarn install
```

## Configuration

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

## Running

### Development
```bash
npm run dev
# or
yarn dev
```

Visit http://localhost:3000

### Production
```bash
npm run build
npm start
```

## Project Structure

```
app/
├── layout.tsx              # Root layout with sidebar
├── providers.tsx           # React Query provider
├── page.tsx                # Dashboard overview
├── runs/                   # Run history page
├── drift/                  # Drift alerts page
├── tables/[tableName]/     # Dynamic table details
└── metrics/                # Metrics & analytics

components/
├── Sidebar.tsx             # Navigation sidebar
├── KPICard.tsx             # KPI display cards
├── RunsTable.tsx           # Runs data table
├── DriftAlertsTable.tsx    # Drift alerts table
└── FilterPanel.tsx         # Filter controls

lib/
└── api.ts                  # API client functions
```

## Pages

### Dashboard (/)
- KPI cards
- Recent runs
- Recent drift alerts
- Warehouse breakdown

### Runs (/runs)
- Full run history
- Advanced filtering
- Export functionality

### Drift Detection (/drift)
- Drift alerts list
- Severity filtering
- Detailed metrics

### Table Metrics (/tables/[name])
- Table-specific metrics
- Row count trends
- Column-level breakdown

### Metrics (/metrics)
- Analytics charts
- Warehouse distribution
- Trend analysis

## Components

### Sidebar
Navigation menu with current page highlighting.

### KPICard
Displays key metrics with optional trend indicators.

### RunsTable
Paginated table of profiling runs with status indicators.

### DriftAlertsTable
Shows drift alerts with severity badges and details.

### FilterPanel
Reusable filter controls for warehouse, schema, table, date range.

## API Integration

All API calls are in `lib/api.ts`:

```typescript
import { fetchRuns, fetchDriftAlerts, fetchTableMetrics } from '@/lib/api'
```

Uses TanStack Query for caching and state management.

## Styling

Tailwind CSS with custom theme colors in `tailwind.config.ts`.

### Custom Colors
- Primary: Blue (#0ea5e9)
- Success: Green (#10b981)
- Warning: Orange (#f59e0b)
- Danger: Red (#ef4444)

## Adding New Features

### New Page
1. Create `app/your-page/page.tsx`
2. Add route to `components/Sidebar.tsx`
3. Optionally add API function in `lib/api.ts`

### New Component
1. Create in `components/YourComponent.tsx`
2. Import and use in pages

## Charts

Using Recharts for all visualizations:
- Line charts for trends
- Bar charts for comparisons
- Pie charts for distributions

## Export Functionality

Export buttons trigger downloads:
```typescript
const data = await exportRuns(filters)
const blob = new Blob([JSON.stringify(data, null, 2)])
// Trigger download...
```

## TODO / Future Enhancements

- [ ] Dark mode toggle
- [ ] User preferences persistence
- [ ] Advanced chart interactions
- [ ] Real-time updates with WebSockets
- [ ] CSV export implementation
- [ ] Custom dashboard builder

## Troubleshooting

### API Connection Issues
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure backend is running on port 8000
- Check CORS settings in backend

### No Data Showing
- Run sample data generator in backend
- Or perform actual Baselinr profiling

### Build Errors
```bash
rm -rf .next node_modules
npm install
npm run build
```

