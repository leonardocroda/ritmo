# Ritmo frontend — Next.js 16 (build standalone, AD-007)
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# URL da API lida pelo cliente — o Next inlina NEXT_PUBLIC_* durante o
# build, então o valor chega como build arg e vira env antes de `next build`.
# (AD-020: com o rewrite same-origin o cliente usa base relativa; o que o
# build precisa é o destino INTERNO do rewrite — o hostname do serviço
# backend na rede do compose.)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=${BACKEND_URL}

COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
