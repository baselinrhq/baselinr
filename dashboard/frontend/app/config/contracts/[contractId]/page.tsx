import { Suspense } from 'react'
import ContractDetailClient from './ContractDetailClient'

// Required for static export with dynamic routes
export async function generateStaticParams(): Promise<Array<{ contractId: string }>> {
  // Return placeholder for static export
  // In demo mode, this route will be handled client-side
  return [{ contractId: '__placeholder__' }]
}

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

