import type { NextConfig } from "next";

// Auth (emenda UAT, 20/10 — AD-020): o frontend chama a API PELO PRÓPRIO
// Next (rewrite same-origin). O cookie de sessão passa a valer para o host
// que o usuário abriu (localhost:3000 e IP-da-LAN:3000 funcionam), o proxy
// otimista vê o cookie em qualquer host e o CORS deixa de ser requisito.
// O destino é resolvido no start do servidor: no compose, BACKEND_URL é o
// hostname do serviço; no dev (`npm run dev`), o fallback é localhost:8000.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // standalone gera o server.js autocontido para o Docker/compose. Na
  // Vercel não há self-hosting: o build deles (VERCEL=1) segue o output
  // nativo da plataforma — standalone lá só desperdiçaria build.
  output: process.env.VERCEL ? undefined : "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
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
