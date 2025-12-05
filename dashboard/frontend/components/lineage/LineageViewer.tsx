'use client';

/**
 * Interactive lineage graph viewer using Cytoscape.js
 */

import { useEffect, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import dagre from 'cytoscape-dagre';
import cytoscape, { Core } from 'cytoscape';
import { LineageGraphResponse } from '@/types/lineage';

// Register dagre layout
cytoscape.use(dagre);

interface LineageViewerProps {
  graph: LineageGraphResponse | null;
  loading?: boolean;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  layout?: 'hierarchical' | 'circular' | 'force-directed';
}

export default function LineageViewer({
  graph,
  loading = false,
  onNodeClick,
  onEdgeClick,
  layout = 'hierarchical',
}: LineageViewerProps) {
  const cyRef = useRef<Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Convert graph to Cytoscape format
  const elements = graph
    ? [
        ...graph.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            schema: node.schema,
            table: node.table,
            column: node.column,
            ...node.metadata,
          },
          classes: [
            node.type,
            ...(node.metadata?.is_root ? ['root'] : []),
            ...(node.metadata?.has_drift
              ? [`drift-${node.metadata.drift_severity || 'low'}`]
              : []),
          ].join(' '),
        })),
        ...graph.edges.map((edge, idx) => ({
          data: {
            id: `edge-${idx}`,
            source: edge.source,
            target: edge.target,
            label: edge.relationship_type,
            confidence: edge.confidence,
            provider: edge.provider,
          },
          classes: [
            edge.confidence < 0.5
              ? 'low-confidence'
              : edge.confidence < 0.8
                ? 'medium-confidence'
                : 'high-confidence',
          ].join(' '),
        })),
      ]
    : [];

  // Cytoscape stylesheet
  const stylesheet: cytoscape.Stylesheet[] = [
    {
      selector: 'node',
      style: {
        'background-color': '#e5e7eb',
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '12px',
        'font-weight': 'normal',
        'color': '#1f2937',
        'width': 100,
        'height': 50,
        'shape': 'roundrectangle',
        'border-width': 2,
        'border-color': '#9ca3af',
      },
    },
    {
      selector: 'node[type="table"]',
      style: {
        'shape': 'roundrectangle',
        'width': 120,
        'height': 60,
      },
    },
    {
      selector: 'node[type="column"]',
      style: {
        'shape': 'ellipse',
        'width': 80,
        'height': 80,
      },
    },
    {
      selector: 'node.root',
      style: {
        'background-color': '#dbeafe',
        'border-width': 3,
        'border-color': '#3b82f6',
        'font-weight': 'bold',
      },
    },
    {
      selector: 'node.drift-high',
      style: {
        'background-color': '#fee2e2',
        'border-color': '#ef4444',
        'border-width': 3,
      },
    },
    {
      selector: 'node.drift-medium',
      style: {
        'background-color': '#fef3c7',
        'border-color': '#f59e0b',
        'border-width': 2,
      },
    },
    {
      selector: 'node.drift-low',
      style: {
        'background-color': '#fff7ed',
        'border-color': '#fb923c',
        'border-width': 2,
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#3b82f6',
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#9ca3af',
        'target-arrow-color': '#9ca3af',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '10px',
        'text-rotation': 'autorotate',
        'text-margin-y': -10,
      },
    },
    {
      selector: 'edge.high-confidence',
      style: {
        'line-color': '#4b5563',
        'width': 3,
        'line-style': 'solid',
      },
    },
    {
      selector: 'edge.medium-confidence',
      style: {
        'line-color': '#6b7280',
        'width': 2,
        'line-style': 'dashed',
      },
    },
    {
      selector: 'edge.low-confidence',
      style: {
        'line-color': '#9ca3af',
        'width': 1,
        'line-style': 'dotted',
      },
    },
  ];

  // Layout configuration
  const getLayout = () => {
    switch (layout) {
      case 'hierarchical':
        return {
          name: 'dagre',
          rankDir: 'TB',
          nodeSep: 50,
          rankSep: 100,
          spacingFactor: 1.2,
        };
      case 'circular':
        return {
          name: 'circle',
          radius: 300,
          startAngle: 0,
          sweep: 360,
        };
      case 'force-directed':
        return {
          name: 'cose',
          idealEdgeLength: 100,
          nodeOverlap: 20,
          refresh: 20,
          fit: true,
          padding: 30,
          randomize: false,
          componentSpacing: 100,
          nodeRepulsion: 400000,
          nestingFactor: 5,
          gravity: 0.25,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
        };
      default:
        return { name: 'dagre', rankDir: 'TB' };
    }
  };

  // Handle graph ready
  const handleCyReady = (cy: Core) => {
    cyRef.current = cy;

    // Node click handler
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeId = node.id();
      setSelectedNode(nodeId);
      if (onNodeClick) {
        onNodeClick(nodeId);
      }
    });

    // Edge click handler
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      const edgeId = edge.id();
      if (onEdgeClick) {
        onEdgeClick(edgeId);
      }
    });

    // Pan and zoom controls
    cy.on('pan', () => {});
    cy.on('zoom', () => {});

    // Fit graph on initial load
    if (graph && graph.nodes.length > 0) {
      cy.fit(undefined, 50);
    }
  };

  // Update layout when it changes
  useEffect(() => {
    if (cyRef.current && graph && graph.nodes.length > 0) {
      const layoutInstance = cyRef.current.layout(getLayout());
      layoutInstance.run();
    }
  }, [layout, graph]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-gray-600">Loading lineage graph...</div>
        </div>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">No lineage data available</p>
          <p className="text-sm">Select a table to view its lineage</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-white rounded-lg border border-gray-200">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={stylesheet}
        cy={(cy) => handleCyReady(cy)}
        layout={getLayout()}
        minZoom={0.1}
        maxZoom={2}
        wheelSensitivity={0.2}
      />
    </div>
  );
}




