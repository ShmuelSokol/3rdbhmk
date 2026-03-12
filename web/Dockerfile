FROM node:20-alpine AS base

# Install dependencies for Prisma, PDF processing, and node-canvas
RUN apk add --no-cache openssl poppler-utils tesseract-ocr tesseract-ocr-data-eng \
    cairo pango giflib libjpeg-turbo freetype fontconfig ttf-freefont

FROM base AS deps
RUN apk add --no-cache build-base g++ cairo-dev pango-dev giflib-dev libjpeg-turbo-dev freetype-dev python3
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Cache bust to force rebuild when source changes
ARG CACHEBUST=1

# Build args for NEXT_PUBLIC_ vars
ENV NEXT_TELEMETRY_DISABLED=1

RUN npx prisma@5 generate
RUN npm run build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/node_modules/@prisma ./node_modules/@prisma
COPY --from=builder /app/node_modules/@supabase ./node_modules/@supabase
COPY --from=builder /app/node_modules/sharp ./node_modules/sharp

# Create tmp directory for PDF processing
RUN mkdir -p /tmp/bhmk && chown -R nextjs:nodejs /tmp/bhmk

USER nextjs

ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
