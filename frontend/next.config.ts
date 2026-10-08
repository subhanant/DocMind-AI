import type { NextConfig } from "next";

/**
 * Optional same-origin API proxy.
 *
 * By default the browser talks to the FastAPI service directly via
 * `NEXT_PUBLIC_API_URL` (http://localhost:8000 in local development), which
 * requires the backend to list the frontend origin in its CORS config.
 *
 * Set `API_PROXY_TARGET` (e.g. `http://127.0.0.1:8000`) to instead route
 * `/api/*` through the Next.js server, and set `NEXT_PUBLIC_API_URL=""` so the
 * client uses same-origin relative URLs. Useful behind a single public hostname
 * (previews, containers) where a second origin is not reachable.
 *
 * When the variable is unset no rewrite is registered and behaviour is unchanged.
 */
const API_PROXY_TARGET = process.env.API_PROXY_TARGET?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!API_PROXY_TARGET) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${API_PROXY_TARGET}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
