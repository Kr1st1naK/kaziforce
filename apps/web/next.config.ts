import type { NextConfig } from "next";

// Headers that cost nothing and help on any host. HSTS is for a production build only: set on a
// development host it would pin a browser to HTTPS for localhost, and it means nothing over HTTP.
// No Content-Security-Policy yet: Next's inline scripts need a per-request nonce to allow, and
// that belongs with the deployment (docs/privacy-and-keys.md).
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  ...(process.env.NODE_ENV === "production"
    ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }]
    : []),
];

const nextConfig: NextConfig = {
  // The dev-tools badge would otherwise sit in the corner of every thesis figure.
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
