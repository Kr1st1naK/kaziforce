import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dev-tools badge would otherwise sit in the corner of every thesis figure.
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;
