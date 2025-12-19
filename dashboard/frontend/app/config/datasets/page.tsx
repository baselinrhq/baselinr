import { Suspense } from 'react'
import DatasetsPageClient from './DatasetsPageClient'

export default function DatasetsPage() {
  return (
    <Suspense fallback={<div className="p-6"><div className="text-sm text-slate-400">Loading...</div></div>}>
      <DatasetsPageClient />
    </Suspense>
  )
}
