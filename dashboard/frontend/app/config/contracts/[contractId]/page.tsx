import { Suspense } from 'react'
import ContractDetailClient from './ContractDetailClient'

export default function ContractDetailPage({
  params,
}: {
  params: { contractId: string }
}) {
  return (
    <Suspense fallback={<div className="p-6"><div className="text-sm text-slate-400">Loading...</div></div>}>
      <ContractDetailClient contractId={params.contractId} />
    </Suspense>
  )
}

