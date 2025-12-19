import QualityScoreDetailClient from './QualityScoreDetailClient'

// Required for static export with dynamic routes
export async function generateStaticParams() {
  return []
}

export default function QualityScoreDetailPage() {
  return <QualityScoreDetailClient />
}
