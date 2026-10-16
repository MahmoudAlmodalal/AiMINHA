import type { NextConfig } from "next";

const apiOrigin = process.env.API_INTERNAL_ORIGIN ?? "http://127.0.0.1:8000";
const parsedOrigin = new URL(apiOrigin);
if (
  !["http:", "https:"].includes(parsedOrigin.protocol) ||
  parsedOrigin.username || parsedOrigin.password ||
  parsedOrigin.pathname !== "/" || parsedOrigin.search || parsedOrigin.hash
) {
  throw new Error("API_INTERNAL_ORIGIN must be an origin without credentials, path or query.");
}

const config: NextConfig = {
  // Development startup must not write generated instructions into the source tree.
  agentRules: false,
  poweredByHeader: false,
  transpilePackages: ["@minhaai/contracts"],
  async redirects() {
    return [{ source: "/", destination: "/ar", permanent: false }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${parsedOrigin.origin}/api/:path*` }];
  },
};
export default config;
