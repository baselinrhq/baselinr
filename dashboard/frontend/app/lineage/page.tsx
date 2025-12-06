'use client';

/**
 * Full-page lineage exploration interface
 */

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getLineageGraph, getAllTables, searchTables } from '@/lib/api/lineage';
import { LineageGraphResponse, TableInfoResponse } from '@/types/lineage';
import LineageViewer from '@/components/lineage/LineageViewer';

function LineageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [, setTables] = useState<TableInfoResponse[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<TableInfoResponse[]>([]);
  
  const [selectedTable, setSelectedTable] = useState(searchParams.get('table') || '');
  const [selectedSchema, setSelectedSchema] = useState(searchParams.get('schema') || '');
  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>(
    (searchParams.get('direction') as 'upstream' | 'downstream' | 'both') || 'both'
  );
  const [depth, setDepth] = useState(Number(searchParams.get('depth')) || 3);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0);
  const [layout, setLayout] = useState<'hierarchical' | 'circular' | 'force-directed'>('hierarchical');

  const [graph, setGraph] = useState<LineageGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available tables
  useEffect(() => {
    const fetchTables = async () => {
      try {
        const data = await getAllTables(100);
        setTables(data);
      } catch (err) {
        console.error('Failed to fetch tables:', err);
      }
    };
    fetchTables();
  }, []);

  // Handle search
  useEffect(() => {
    const doSearch = async () => {
      if (searchQuery.length < 2) {
        setSearchResults([]);
        return;
      }
      try {
        const results = await searchTables(searchQuery);
        setSearchResults(results);
      } catch (err) {
        console.error('Search failed:', err);
      }
    };

    const timer = setTimeout(doSearch, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch lineage when parameters change
  useEffect(() => {
    if (!selectedTable) {
      setGraph(null);
      return;
    }

    const fetchLineage = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getLineageGraph({
          table: selectedTable,
          schema: selectedSchema || undefined,
          direction,
          depth,
          confidenceThreshold,
        });
        setGraph(data);

        // Update URL
        const params = new URLSearchParams({
          table: selectedTable,
          ...(selectedSchema && { schema: selectedSchema }),
          direction,
          depth: String(depth),
        });
        router.replace(`/lineage?${params}`, { scroll: false });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch lineage');
        setGraph(null);
      } finally {
        setLoading(false);
      }
    };

    fetchLineage();
  }, [selectedTable, selectedSchema, direction, depth, confidenceThreshold]);

  const handleTableSelect = (table: TableInfoResponse) => {
    setSelectedTable(table.table);
    setSelectedSchema(table.schema);
    setSearchQuery('');
    setSearchResults([]);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Lineage Explorer</h1>
        <p className="text-sm text-gray-600 mt-1">
          Visualize and explore data lineage relationships
        </p>
      </div>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-120px)]">
        {/* Control Panel - Sidebar */}
        <div className="w-80 bg-white border-r border-gray-200 p-6 overflow-y-auto">
          <div className="space-y-6">
            {/* Table Search/Select */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Table
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search tables..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {searchResults.map((table) => (
                      <button
                        key={`${table.schema}.${table.table}`}
                        onClick={() => handleTableSelect(table)}
                        className="w-full px-3 py-2 text-left hover:bg-gray-100 focus:bg-gray-100"
                      >
                        <div className="font-medium text-gray-900">{table.table}</div>
                        <div className="text-xs text-gray-500">{table.schema}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              {selectedTable && (
                <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                  <div className="font-medium text-blue-900">{selectedTable}</div>
                  {selectedSchema && (
                    <div className="text-xs text-blue-600">{selectedSchema}</div>
                  )}
                </div>
              )}
            </div>

            {/* Direction */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Direction
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as 'upstream' | 'downstream' | 'both')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="both">Both</option>
                <option value="upstream">Upstream</option>
                <option value="downstream">Downstream</option>
              </select>
            </div>

            {/* Depth */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Depth: {depth}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            {/* Confidence Threshold */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Min Confidence: {confidenceThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.0</span>
                <span>1.0</span>
              </div>
            </div>

            {/* Layout */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Layout
              </label>
              <select
                value={layout}
                onChange={(e) => setLayout(e.target.value as 'hierarchical' | 'circular' | 'force-directed')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="hierarchical">Hierarchical</option>
                <option value="circular">Circular</option>
                <option value="force-directed">Force-Directed</option>
              </select>
            </div>

            {/* Stats */}
            {graph && (
              <div className="pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Graph Stats</h3>
                <div className="space-y-1 text-sm text-gray-600">
                  <div>Nodes: {graph.nodes.length}</div>
                  <div>Edges: {graph.edges.length}</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Graph Area */}
        <div className="flex-1 p-6">
          {loading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-gray-500">Loading lineage graph...</div>
            </div>
          )}

          {error && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-red-600 font-medium mb-2">Error</div>
                <div className="text-gray-600">{error}</div>
              </div>
            </div>
          )}

          {!loading && !error && !selectedTable && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-gray-400 text-lg mb-2">No table selected</div>
                <div className="text-gray-500 text-sm">
                  Search and select a table to view its lineage
                </div>
              </div>
            </div>
          )}

          {!loading && !error && graph && (
            <div className="h-full flex flex-col">
              <div className="mb-4 bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">
                      Lineage Graph
                    </h2>
                    <p className="text-sm text-gray-600">
                      {graph.nodes.length} nodes, {graph.edges.length} relationships
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs text-gray-500">
                    <span>Zoom: Scroll wheel</span>
                    <span>•</span>
                    <span>Pan: Click & drag</span>
                  </div>
                </div>
              </div>

              <div className="flex-1 min-h-0">
                <LineageViewer
                  graph={graph}
                  loading={loading}
                  layout={layout}
                  onNodeClick={(nodeId) => {
                    console.log('Node clicked:', nodeId);
                  }}
                  onEdgeClick={(edgeId) => {
                    console.log('Edge clicked:', edgeId);
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LineagePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LineageContent />
    </Suspense>
  );
}
