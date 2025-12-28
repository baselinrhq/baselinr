import { Suspense } from 'react'
import ContractsPageClient from './ContractsPageClient'

export default function ContractsPage() {
  return (
    <Suspense fallback={<div className="p-6"><div className="text-sm text-slate-400">Loading contracts...</div></div>}>
      <ContractsPageClient />
    </Suspense>
  )
}

