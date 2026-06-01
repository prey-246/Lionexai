/** @type {import('next').NextConfig} */
const nextConfig = {
  // Ignore ESLint errors during the build.
  eslint: { ignoreDuringBuilds: true },
  // Ignore TypeScript errors during the build.
  typescript: { ignoreBuildErrors: true },
  // Downgrade the Suspense error to a warning to prevent build failures.
  experimental: { missingSuspenseWithCSRBailout: false },
  // Implement reverse proxy for API calls
  async rewrites() {
    return [
      {
        // Route all frontend /api/* requests...
        source: '/api/:path*',
        // ...to the internal backend service URL defined in Render's env vars.
        // This also proxies WebSockets.
        destination: `${process.env.INTERNAL_API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;