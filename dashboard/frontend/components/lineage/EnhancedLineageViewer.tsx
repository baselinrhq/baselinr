'use client'

import { useState, useRef } from 'react'
import { ZoomIn, ZoomOut, Maximize2, Download, RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import LineageViewer from './LineageViewer'
import type { LineageGraphResponse } from '@/types/lineage'
import { Core } from 'cytoscape'

interface EnhancedLineageViewerProps {
  graph: LineageGraphResponse | null
  loading?: boolean
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (edgeId: string) => void
  layout?: 'hierarchical' | 'circular' | 'force-directed' | 'breadth-first' | 'grid'
  showControls?: boolean
  showExport?: boolean
  showFullscreen?: boolean
}

export default function EnhancedLineageViewer({
  graph,
  loading = false,
  onNodeClick,
  onEdgeClick,
  layout = 'hierarchical',
  showControls = true,
  showExport = true,
  showFullscreen = true,
}: EnhancedLineageViewerProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const cyRef = useRef<Core | null>(null)

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2)
    }
  }

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8)
    }
  }

  const handleFit = () => {
    if (cyRef.current && graph && graph.nodes.length > 0) {
      cyRef.current.fit(undefined, 50)
    }
  }

  const handleReset = () => {
    if (cyRef.current) {
      cyRef.current.reset()
      cyRef.current.fit(undefined, 50)
    }
  }

  const handleExportPNG = () => {
    if (cyRef.current) {
      const png = cyRef.current.png({ output: 'blob', bg: '#0f172a', full: true })
      const url = URL.createObjectURL(png)
      const link = document.createElement('a')
      link.href = url
      link.download = `lineage-${Date.now()}.png`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleExportSVG = () => {
    if (cyRef.current) {
      // svg() method exists at runtime but isn't in TypeScript types
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cyInstance = cyRef.current as any
      const svg = cyInstance.svg({ full: true, bg: '#0f172a' })
      const blob = new Blob([svg], { type: 'image/svg+xml' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `lineage-${Date.now()}.svg`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleExportJSON = () => {
    if (graph) {
      const dataStr = JSON.stringify(graph, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `lineage-${Date.now()}.json`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleNodeClick = (nodeId: string) => {
    if (onNodeClick) {
      onNodeClick(nodeId)
    }
  }

  return (
    <>
      <div className="relative w-full h-full bg-surface-900/50 rounded-lg border border-surface-700/50">
        {/* Controls Toolbar */}
        {showControls && (
          <div className="absolute top-4 right-4 z-10 flex items-center gap-2 bg-surface-800 rounded-lg shadow-xl shadow-black/20 border border-surface-700 p-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleFit}
              title="Fit to Screen"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              title="Reset View"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
            {showExport && (
              <>
                <div className="w-px h-6 bg-surface-600 mx-1" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportPNG}
                  title="Export PNG"
                >
                  <Download className="w-4 h-4" />
                </Button>
              </>
            )}
            {showFullscreen && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsFullscreen(true)}
                title="Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        )}

        {/* Graph Viewer */}
        <LineageViewer
          graph={graph}
          loading={loading}
          onNodeClick={handleNodeClick}
          onEdgeClick={onEdgeClick}
          layout={layout === 'breadth-first' || layout === 'grid' ? 'hierarchical' : layout}
          onCyReady={(cy) => {
            cyRef.current = cy
          }}
        />
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <Modal
          isOpen={isFullscreen}
          onClose={() => setIsFullscreen(false)}
          size="xl"
          title="Lineage Graph - Fullscreen"
        >
          <div className="h-[calc(100vh-200px)]">
            <EnhancedLineageViewer
              graph={graph}
              loading={loading}
              onNodeClick={handleNodeClick}
              onEdgeClick={onEdgeClick}
              layout={layout}
              showControls={true}
              showExport={true}
              showFullscreen={false}
            />
          </div>
        </Modal>
      )}

      {/* Export Menu (could be a dropdown in the future) */}
      {showExport && (
        <div className="hidden">
          <button onClick={handleExportSVG}>Export SVG</button>
          <button onClick={handleExportJSON}>Export JSON</button>
        </div>
      )}
    </>
  )
}

