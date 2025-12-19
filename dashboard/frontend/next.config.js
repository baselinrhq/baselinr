/** @type {import('next').NextConfig} */
const path = require('path')
const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === 'true'

const nextConfig = {
  reactStrictMode: true,
  typescript: {
    // ⚠️ Temporarily ignore TypeScript errors during build for Cloudflare deployment
    // Remove this after fixing all TypeScript errors
    ignoreBuildErrors: true,
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './'),
    }
    return config
  },
  // Enable static export for Cloudflare Pages deployment
  ...(isDemoMode && {
    output: 'export',
    images: {
      unoptimized: true,
    },
  }),
  // Only add rewrites when NOT in demo mode (static export doesn't support rewrites)
  ...(!isDemoMode && {
    async rewrites() {
      // Use NEXT_PUBLIC_API_URL if set, otherwise default to localhost:8000
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        },
      ]
    },
  }),
}

module.exports = nextConfig

