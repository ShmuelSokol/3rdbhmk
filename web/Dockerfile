FROM node:20-slim AS base

# Install dependencies for Prisma, PDF processing, and node-canvas
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl poppler-utils tesseract-ocr tesseract-ocr-eng \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgif7 libjpeg62-turbo \
    libfreetype6 fontconfig fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ libcairo2-dev libpango1.0-dev libgif-dev \
    libjpeg62-turbo-dev libfreetype6-dev python3 \
    && rm -rf /var/lib/apt/lists/*
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

# Install Playwright Chromium for HTML-to-PDF rendering
RUN npx playwright install --with-deps chromium

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
COPY --from=builder /app/node_modules/canvas ./node_modules/canvas
COPY --from=builder /app/node_modules/playwright ./node_modules/playwright
COPY --from=builder /app/node_modules/playwright-core ./node_modules/playwright-core

# Copy Playwright browsers + dependencies from builder
COPY --from=builder /root/.cache/ms-playwright /home/nextjs/.cache/ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/home/nextjs/.cache/ms-playwright
ENV HOME=/home/nextjs
# Install Chromium runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    libxfixes3 libx11-xcb1 libxcb1 libx11-6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
RUN chown -R nextjs:nodejs /home/nextjs/.cache

# Create tmp directory for PDF processing
RUN mkdir -p /tmp/bhmk && chown -R nextjs:nodejs /tmp/bhmk

USER nextjs

ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
