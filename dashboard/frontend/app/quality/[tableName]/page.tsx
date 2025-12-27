import { Suspense } from 'react'
import QualityScoreDetailClient from './QualityScoreDetailClient'
import fs from 'fs'
import path from 'path'

// Required for static export with dynamic routes
// Generate params for all tables from demo data
export async function generateStaticParams(): Promise<Array<{ tableName: string }>> {
  // In demo mode, load table names from demo data
  if (process.env.NEXT_PUBLIC_DEMO_MODE === 'true') {
    try {
      const demoDataPath = path.join(process.cwd(), 'public', 'demo_data', 'tables.json')
      if (fs.existsSync(demoDataPath)) {
        const tablesData = JSON.parse(fs.readFileSync(demoDataPath, 'utf-8'))
        if (Array.isArray(tablesData)) {
          // Extract unique table names and URL-encode them
          interface TableData {
            table_name?: string
          }
          const tableNames = [...new Set(
            tablesData
              .map((t: TableData) => t.table_name)
              .filter((name): name is string => Boolean(name))
          )]
          return tableNames.map(tableName => ({
            tableName: encodeURIComponent(tableName)
          }))
        }
      }
    } catch (error) {
      console.warn('Failed to load table names for generateStaticParams:', error)
    }
  }
  
  // Fallback: return placeholder if demo data not available
  return [{ tableName: '__placeholder__' }]
}

export default function QualityScoreDetailPage() {
  return (
    <Suspense fallback={<div className="p-6"><div className="text-sm text-slate-400">Loading...</div></div>}>
      <QualityScoreDetailClient />
    </Suspense>
  )
}
