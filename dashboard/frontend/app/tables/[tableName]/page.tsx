import { Suspense } from 'react'
import TableMetricsClient from './TableMetricsClient'

// Allow dynamic params for static export (client-side rendering)
export const dynamicParams = true

// Required for static export with dynamic routes
// Return a placeholder to satisfy static export requirements
// Actual pages will be rendered client-side on-demand
export async function generateStaticParams(): Promise<Array<{ tableName: string }>> {
  return [{ tableName: '__placeholder__' }]
}

export default function TableMetricsPage() {
  return (
    <Suspense fallback={<div className="p-6"><div className="text-sm text-slate-400">Loading...</div></div>}>
      <TableMetricsClient />
    </Suspense>
  )
}
