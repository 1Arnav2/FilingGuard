import type { NextConfig } from "next";

const dev = process.env.NODE_ENV !== "production";

// Production is a static export served by the FastAPI app on the same origin. In development the
// Next dev server forwards /api to a local uvicorn, so the client always calls same-origin /api.
const config: NextConfig = dev
  ? {
      async rewrites() {
        const api = process.env.FILINGGUARD_API ?? "http://127.0.0.1:8000";
        return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
      },
    }
  : { output: "export", trailingSlash: true, images: { unoptimized: true } };

export default config;
