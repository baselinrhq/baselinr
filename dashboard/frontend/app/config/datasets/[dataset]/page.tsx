import DatasetDetailClient from './DatasetDetailClient'

// Required for static export with dynamic routes
export async function generateStaticParams() {
  return []
}

export default function DatasetDetailPage() {
  return <DatasetDetailClient />
}
