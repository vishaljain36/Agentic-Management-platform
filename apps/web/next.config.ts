import type { NextConfig } from "next";

/**
 * Backend API host — defaults to localhost:8000 for local dev.
 * In production, set NEXT_PUBLIC_API_URL to the deployed backend URL.
 */
const API_HOST = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["db"],

  // ------------------------------------------------------------------
  // Reverse proxy rewrites: route /api/backend/* through Next.js to
  // the FastAPI backend, eliminating CORS issues for SSE / WebSocket
  // streaming and standard API calls from the browser.
  // ------------------------------------------------------------------
  async rewrites() {
    return [
      // SSE streaming endpoint — proxied to avoid browser CORS on EventSource
      {
        source: "/api/backend/workflow/stream/:path*",
        destination: `${API_HOST}/api/v1/workflow/stream/:path*`,
      },
      // WebSocket upgrade endpoint
      {
        source: "/api/backend/ws/:path*",
        destination: `${API_HOST}/api/v1/ws/:path*`,
      },
      // General backend API passthrough
      {
        source: "/api/backend/:path*",
        destination: `${API_HOST}/api/v1/:path*`,
      },
    ];
  },

  // ------------------------------------------------------------------
  // Production security headers
  // ------------------------------------------------------------------
  async headers() {
    return [
      {
        // Apply security headers to all routes
        source: "/(.*)",
        headers: [
          // Prevent clickjacking by disallowing iframe embedding
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          // Prevent MIME type sniffing
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          // Enable XSS protection in older browsers
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          // Referrer policy — send origin only on cross-origin requests
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          // DNS prefetch control — allow DNS prefetching for performance
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          // Strict Transport Security — enforce HTTPS for 1 year, include subdomains
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
          // Permissions Policy — restrict sensitive browser APIs
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
          // Content Security Policy
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              `connect-src 'self' ${API_HOST} ws: wss: https://cloud.langfuse.com`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
