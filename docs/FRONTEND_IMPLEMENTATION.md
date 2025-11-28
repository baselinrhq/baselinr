# Lineage Visualization Frontend Implementation Guide

This document outlines the React/TypeScript frontend components needed to complete the lineage visualization feature in the Baselinr dashboard.

## Overview

The backend API endpoints have been implemented and are ready to serve lineage data. The frontend needs interactive React components to visualize and explore this data.

## Required Components

### 1. LineageViewer Component

**File:** `dashboard/frontend/components/LineageViewer.tsx`

Main component for rendering interactive lineage graphs using Cytoscape.js.

**Key Features:**
- Cytoscape.js graph rendering
- Zoom, pan, fit controls
- Layout switching (hierarchical, circular, force-directed)
- Node/edge selection and highlighting
- Search and filtering
- Export to PNG/SVG

**Props Interface:**
```typescript
interface LineageViewerProps {
  initialTable?: string;
  initialSchema?: string;
  maxDepth?: number;
  direction?: 'upstream' | 'downstream' | 'both';
  showDrift?: boolean;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
}
```

**Dependencies:**
```json
{
  "cytoscape": "^3.27.0",
  "cytoscape-dagre": "^2.5.0",
  "react-cytoscapejs": "^2.0.0"
}
```

**Styling:**
- Tables: rectangles with rounded corners
- Columns: ellipses
- Root node: bold border, blue background
- Drift nodes: red/yellow/orange based on severity
- Edge thickness: proportional to confidence score

### 2. LineageControlPanel Component

**File:** `dashboard/frontend/components/LineageControlPanel.tsx`

Controls for adjusting lineage visualization parameters.

**Controls:**
- Table selector (autocomplete dropdown)
- Direction toggle (upstream/downstream/both)
- Depth slider (1-10)
- Confidence threshold slider (0-1)
- Layout selector dropdown
- Filter options (by provider, confidence, etc.)
- Show drift toggle
- Export button

**Example:**
```tsx
<LineageControlPanel
  table={selectedTable}
  onTableChange={setSelectedTable}
  direction={direction}
  onDirectionChange={setDirection}
  depth={depth}
  onDepthChange={setDepth}
  onExport={handleExport}
/>
```

### 3. LineagePage Component

**File:** `dashboard/frontend/app/lineage/page.tsx`

Full-page lineage exploration interface.

**Layout:**
```
┌─────────────────────────────────────┐
│  Header / Breadcrumbs               │
├─────────────┬───────────────────────┤
│             │                       │
│  Control    │    Graph Viewer      │
│  Panel      │    (Cytoscape)       │
│  (sidebar)  │                       │
│             │                       │
├─────────────┴───────────────────────┤
│  Node Details Panel (footer)        │
└─────────────────────────────────────┘
```

**Features:**
- URL state management (table, depth, direction in query params)
- Loading states
- Error handling
- Empty state (no lineage data)

### 4. LineageMiniGraph Component

**File:** `dashboard/frontend/components/LineageMiniGraph.tsx`

Compact lineage widget for embedding in other pages.

**Features:**
- Show immediate upstream/downstream only (depth 1)
- Simplified controls
- Click to navigate to full lineage page
- Fixed small size (e.g., 400x300px)

**Usage:**
```tsx
<LineageMiniGraph
  table="orders"
  schema="public"
  direction="upstream"
  onExpand={() => router.push('/lineage?table=orders')}
/>
```

### 5. NodeDetailsPanel Component

**File:** `dashboard/frontend/components/NodeDetailsPanel.tsx`

Display detailed information about selected node.

**Content:**
- Node type (table/column)
- Full path (database.schema.table[.column])
- Upstream count
- Downstream count
- Providers list
- Metadata
- Link to table detail page
- Drift information (if applicable)

### 6. TableSearch Component

**File:** `dashboard/frontend/components/TableSearch.tsx`

Autocomplete search for finding tables with lineage.

**Features:**
- Debounced search (300ms)
- Calls `/api/lineage/search?q=...`
- Shows schema.table results
- Keyboard navigation
- Recent searches (localStorage)

## Integration Points

### Update Existing Pages

#### 1. Table Detail Page
**File:** `dashboard/frontend/app/tables/[tableName]/page.tsx`

Add a "Lineage" tab:
```tsx
<Tabs>
  <Tab label="Overview">...</Tab>
  <Tab label="Metrics">...</Tab>
  <Tab label="Lineage">
    <LineageMiniGraph table={tableName} />
  </Tab>
</Tabs>
```

#### 2. Drift Alert Page
**File:** `dashboard/frontend/app/drift/page.tsx`

Show drift propagation:
```tsx
{driftAlert && (
  <DriftImpactSection>
    <h3>Affected Downstream Tables</h3>
    <LineageMiniGraph
      table={driftAlert.tableName}
      direction="downstream"
      showDrift={true}
    />
  </DriftImpactSection>
)}
```

#### 3. Dashboard Home
**File:** `dashboard/frontend/app/page.tsx`

Add lineage summary widget:
```tsx
<LineageSummaryCard>
  <h3>Lineage</h3>
  <p>{lineageStats.tableCount} tables tracked</p>
  <p>{lineageStats.edgeCount} relationships</p>
  <Link href="/lineage">Explore →</Link>
</LineageSummaryCard>
```

#### 4. Navigation Menu
**File:** `dashboard/frontend/components/Sidebar.tsx`

Add lineage nav item:
```tsx
<NavItem href="/lineage" icon={<NetworkIcon />}>
  Lineage
</NavItem>
```

## API Client Functions

**File:** `dashboard/frontend/lib/api/lineage.ts`

```typescript
export async function getLineageGraph(params: {
  table: string;
  schema?: string;
  direction?: string;
  depth?: number;
  confidenceThreshold?: number;
}): Promise<LineageGraphResponse> {
  const query = new URLSearchParams({
    table: params.table,
    direction: params.direction || 'both',
    depth: String(params.depth || 3),
    confidence_threshold: String(params.confidenceThreshold || 0),
    ...(params.schema && { schema: params.schema }),
  });
  
  const res = await fetch(`/api/lineage/graph?${query}`);
  if (!res.ok) throw new Error('Failed to fetch lineage');
  return res.json();
}

export async function getNodeDetails(nodeId: string): Promise<NodeDetailsResponse> {
  const res = await fetch(`/api/lineage/node/${encodeURIComponent(nodeId)}`);
  if (!res.ok) throw new Error('Failed to fetch node details');
  return res.json();
}

export async function searchTables(query: string): Promise<TableInfoResponse[]> {
  const res = await fetch(`/api/lineage/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}
```

## TypeScript Types

**File:** `dashboard/frontend/types/lineage.ts`

```typescript
export interface LineageNode {
  id: string;
  type: 'table' | 'column';
  label: string;
  schema?: string;
  table?: string;
  column?: string;
  database?: string;
  metadata: Record<string, any>;
  metrics?: Record<string, number>;
}

export interface LineageEdge {
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  transformation?: string;
  provider: string;
  metadata: Record<string, any>;
}

export interface LineageGraphResponse {
  nodes: LineageNode[];
  edges: LineageEdge[];
  root_id?: string;
  direction: string;
}

export interface NodeDetailsResponse {
  id: string;
  type: string;
  label: string;
  schema?: string;
  table?: string;
  column?: string;
  upstream_count: number;
  downstream_count: number;
  providers: string[];
}

export interface TableInfoResponse {
  schema: string;
  table: string;
  database?: string;
}
```

## Cytoscape.js Configuration

**Example style configuration:**

```typescript
const cytoscapeStylesheet: cytoscape.Stylesheet[] = [
  {
    selector: 'node',
    style: {
      'background-color': '#666',
      'label': 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': '12px',
      'width': 80,
      'height': 40,
    }
  },
  {
    selector: 'node[type="table"]',
    style: {
      'shape': 'roundrectangle',
    }
  },
  {
    selector: 'node[type="column"]',
    style: {
      'shape': 'ellipse',
    }
  },
  {
    selector: 'node.root',
    style: {
      'background-color': '#4a90e2',
      'border-width': 3,
      'border-color': '#2a5a8a',
    }
  },
  {
    selector: 'node.drift-high',
    style: {
      'background-color': '#ff8787',
      'border-width': 3,
      'border-color': '#ff0000',
    }
  },
  {
    selector: 'edge',
    style: {
      'width': 2,
      'line-color': '#ccc',
      'target-arrow-color': '#ccc',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'label': 'data(relationship_type)',
      'font-size': '10px',
    }
  },
  {
    selector: 'edge.low-confidence',
    style: {
      'line-style': 'dotted',
      'width': 1,
    }
  },
];
```

## Layout Algorithms

Use Cytoscape.js extensions for different layouts:

```typescript
import dagre from 'cytoscape-dagre';
import cola from 'cytoscape-cola';

cytoscape.use(dagre);
cytoscape.use(cola);

// Hierarchical layout
cy.layout({
  name: 'dagre',
  rankDir: 'TB', // Top to bottom
  nodeSep: 50,
  rankSep: 100,
}).run();

// Force-directed layout
cy.layout({
  name: 'cola',
  animate: true,
  refresh: 1,
}).run();
```

## Testing

**File:** `dashboard/frontend/__tests__/lineage/LineageViewer.test.tsx`

```typescript
import { render, screen } from '@testing-library/react';
import { LineageViewer } from '@/components/LineageViewer';

describe('LineageViewer', () => {
  it('renders loading state', () => {
    render(<LineageViewer initialTable="customers" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders graph when data loaded', async () => {
    // Mock API response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          nodes: [{ id: 'A', type: 'table', label: 'A' }],
          edges: [],
        }),
      })
    );

    render(<LineageViewer initialTable="customers" />);
    
    await waitFor(() => {
      expect(screen.getByTestId('cytoscape-container')).toBeInTheDocument();
    });
  });
});
```

## Installation Steps

1. Install dependencies:
```bash
cd dashboard/frontend
npm install cytoscape cytoscape-dagre react-cytoscapejs
```

2. Create component files as outlined above

3. Add route in Next.js app router:
```typescript
// app/lineage/page.tsx
export default function LineagePage() {
  return <LineagePageComponent />;
}
```

4. Update navigation to include lineage link

5. Test with sample lineage data

## Example Usage Flow

1. User navigates to `/lineage`
2. `LineagePage` loads with table search/selector
3. User selects "customers" table
4. API call: `GET /api/lineage/graph?table=customers&depth=3&direction=both`
5. `LineageViewer` renders graph with Cytoscape.js
6. User clicks on a node
7. `NodeDetailsPanel` displays node information
8. User adjusts depth slider
9. Graph re-fetches and re-renders

## Next Steps

1. Implement `LineageViewer` component (most complex)
2. Add `LineageControlPanel` for filters
3. Create `LineagePage` with full layout
4. Integrate `LineageMiniGraph` into existing pages
5. Add navigation menu item
6. Write tests
7. Polish UI/UX and styling

## Resources

- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [React Cytoscape Documentation](https://github.com/plotly/react-cytoscapejs)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Baselinr API Documentation](./api.md)
