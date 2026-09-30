import type { NextConfig } from "next";

// Fully static: `next build` writes plain HTML to out/, readable offline.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
