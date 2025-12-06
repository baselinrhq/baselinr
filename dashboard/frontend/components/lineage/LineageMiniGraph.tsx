'use client';

/**
 * Compact lineage widget for embedding in other pages
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getLineageGraph } from '@/lib/api/lineage';
import { LineageGraphResponse } from '@/types/lineage';

interface LineageMiniGraphProps {
  table: string;
  schema?: string;
  direction?: 'upstream' | 'downstream' | 'both';
  onExpand?: () => void;
}

export default function LineageMiniGraph({
  table,
  schema,
  direction = 'both',
  onExpand,
}: LineageMiniGraphProps) {
  const [graph, setGraph] = useState<LineageGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchLineage = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getLineageGraph({
          table,
          schema,
          direction,
          depth: 1, // Only immediate connections for mini graph
        });
        setGraph(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch lineage');
        console.error('Failed to fetch lineage:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLineage();
  }, [table, schema, direction]);

  const handleExpand = () => {
    if (onExpand) {
      onExpand();
    } else {
      const query = new URLSearchParams({
        table,
        ...(schema && { schema }),
      });
      router.push(`/lineage?${query}`);
    }
  };

  if (loading) {
    return (
      <div className="border border-gray-200 rounded-lg p-4 h-64 flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading lineage...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-gray-200 rounded-lg p-4 h-64 flex items-center justify-center bg-gray-50">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="border border-gray-200 rounded-lg p-4 h-64 flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">No lineage data available</div>
      </div>
    );
  }

  // Simple list view for mini graph
  const upstreamNodes = graph.nodes.filter((n) => 
    graph.edges.some((e) => e.target === graph.root_id && e.source === n.id)
  );
  const downstreamNodes = graph.nodes.filter((n) =>
    graph.edges.some((e) => e.source === graph.root_id && e.target === n.id)
  );

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-semibold text-gray-700">Lineage</h3>
        <button
          onClick={handleExpand}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          View Full Graph →
        </button>
      </div>

      <div className="space-y-4 text-sm">
        {upstreamNodes.length > 0 && (
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">
              Upstream ({upstreamNodes.length})
            </div>
            <div className="space-y-1">
              {upstreamNodes.slice(0, 3).map((node) => (
                <div key={node.id} className="text-gray-700 pl-2 border-l-2 border-blue-300">
                  ↑ {node.label}
                  {node.schema && <span className="text-gray-400 text-xs ml-1">({node.schema})</span>}
                </div>
              ))}
              {upstreamNodes.length > 3 && (
                <div className="text-gray-400 text-xs pl-2">
                  +{upstreamNodes.length - 3} more
                </div>
              )}
            </div>
          </div>
        )}

        <div className="text-center py-2 font-medium text-gray-900">
          {table}
          {schema && <span className="text-gray-500 text-xs ml-1">({schema})</span>}
        </div>

        {downstreamNodes.length > 0 && (
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">
              Downstream ({downstreamNodes.length})
            </div>
            <div className="space-y-1">
              {downstreamNodes.slice(0, 3).map((node) => (
                <div key={node.id} className="text-gray-700 pl-2 border-l-2 border-green-300">
                  ↓ {node.label}
                  {node.schema && <span className="text-gray-400 text-xs ml-1">({node.schema})</span>}
                </div>
              ))}
              {downstreamNodes.length > 3 && (
                <div className="text-gray-400 text-xs pl-2">
                  +{downstreamNodes.length - 3} more
                </div>
              )}
            </div>
          </div>
        )}

        {upstreamNodes.length === 0 && downstreamNodes.length === 0 && (
          <div className="text-center text-gray-400 py-4">
            No immediate dependencies
          </div>
        )}
      </div>
    </div>
  );
}
