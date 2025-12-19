import TableMetricsClient from './TableMetricsClient'

// Required for static export with dynamic routes
export async function generateStaticParams() {
  return []
}

export default function TableMetricsPage() {
  return <TableMetricsClient />
}
