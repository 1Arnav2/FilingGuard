import type { NextConfig } from "next";

// A static export with the results built in (D-079): no rewrites, API routes, server actions or
// middleware, so web/ deploys on its own as a static site.
const config: NextConfig = { output: "export", trailingSlash: true, images: { unoptimized: true } };

export default config;
