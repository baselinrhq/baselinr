import DatasetDetailClient from './DatasetDetailClient'

// Allow dynamic params for static export (client-side rendering)
export const dynamicParams = true

// Required for static export with dynamic routes
// Return a placeholder to satisfy static export requirements
// Actual pages will be rendered client-side on-demand
export async function generateStaticParams(): Promise<Array<{ dataset: string }>> {
  return [{ dataset: '__placeholder__' }]
}

export default function DatasetDetailPage() {
  return <DatasetDetailClient />
}
