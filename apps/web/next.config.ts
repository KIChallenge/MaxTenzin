import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Separate output for production builds so `npm run build` never clobbers a running `next dev`.
  distDir: process.env.NODE_ENV === "production" ? ".next-build" : ".next",
};

export default nextConfig;
