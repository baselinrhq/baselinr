import type { Metadata } from 'next'
import './globals.css'
import Providers from './providers'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'Baselinr Quality Studio',
  description: 'No-code data quality setup and monitoring platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans">
        <Providers>
          <div className="flex h-screen bg-surface-950">
            <Sidebar />
            <main className="flex-1 overflow-auto">
              <div className="min-h-full">
                {children}
              </div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
