import type { Metadata } from 'next'
import './globals.css'
import Providers from './providers'
import Sidebar from '@/components/Sidebar'
import DemoModeBanner from '@/components/DemoModeBanner'

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
            <main className="flex-1 overflow-auto flex flex-col">
              <DemoModeBanner />
              <div className="flex-1 min-h-0">
                {children}
              </div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
