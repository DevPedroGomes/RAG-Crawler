/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  images: {
    unoptimized: true,
  },
  /**
   * Routing scheme:
   *   /api/auth/*    → handled by Next.js (Better Auth handler at app/api/auth/[...all])
   *   /api/backend/* → proxied to the FastAPI backend (Python)
   *
   * The two paths are kept disjoint on purpose so the rewrite never steals
   * Better Auth's own URLs.
   */
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.BACKEND_INTERNAL_URL || "http://localhost:8000"}/:path*`,
      },
    ]
  },
}

export default nextConfig
