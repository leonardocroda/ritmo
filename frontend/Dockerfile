# Ritmo frontend — Next.js 16 (build standalone, AD-007)
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# URL da API lida pelo cliente — o Next inlina NEXT_PUBLIC_* durante o
# build, então o valor chega como build arg e vira env antes de `next build`.
ARG NEXT_PUBLIC_API_URL=http://192.168.15.16/:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

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
