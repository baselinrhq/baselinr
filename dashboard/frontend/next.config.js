/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use NEXT_PUBLIC_API_URL if set, otherwise default to localhost:3005
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3005'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig

