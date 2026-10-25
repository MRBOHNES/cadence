import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Tailwind v4 is wired in through Turbopack's loader (set up by create-next-app).
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
