FROM node:22-alpine

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile --ignore-scripts

# Copy application source
COPY . .

# Build the Next.js application
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Copy the Next.js configuration file
COPY next.config.mjs .

RUN pnpm run build

EXPOSE 3000

CMD ["pnpm", "start"]