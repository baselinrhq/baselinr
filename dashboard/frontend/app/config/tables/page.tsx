'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'

export default function TablesPage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to datasets page with tables tab
    router.replace('/config/datasets?tab=tables')
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loader2 className="h-8 w-8 animate-spin text-cyan-400" />
    </div>
  )
}
