# FROM node:22-alpine

# WORKDIR /app

# # Install dependencies
# COPY package.json pnpm-lock.yaml* ./
# RUN corepack enable pnpm && pnpm install --frozen-lockfile --ignore-scripts

# # Copy application source
# COPY . .

# # Build the Next.js application
# ENV NEXT_TELEMETRY_DISABLED=1
# ENV NODE_ENV=production

# # Copy the Next.js configuration file
# COPY next.config.mjs .

# RUN pnpm run build

# EXPOSE 3000

# CMD ["pnpm", "start"]

# d:\Ewealthtech\Lionexai\frontend\Dockerfile

# Stage 1: Install dependencies in a dedicated 'deps' stage
FROM node:20-alpine AS deps
WORKDIR /app

# Enable pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy only the files needed to install dependencies
COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile --ignore-scripts

# Stage 2: Build the application in a 'builder' stage
FROM node:20-alpine AS builder
WORKDIR /app

# Enable pnpm in this stage as well
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy dependencies from the 'deps' stage
COPY --from=deps /app/node_modules ./node_modules
# Copy the rest of the application source code
COPY . .

# Build the Next.js application.
# Remove pnpm-workspace.yaml if it slipped into the context: this image uses
# pnpm@9, which would otherwise treat it as a workspace and fail the build
# ("packages field missing or empty"). Native build approval is handled via
# the "pnpm" field in package.json and install runs with --ignore-scripts.
ENV NEXT_TELEMETRY_DISABLED=1
RUN rm -f pnpm-workspace.yaml && pnpm build

# Stage 3: Production image - final, lean stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

# Create a non-root user for better security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy only the necessary built artifacts from the 'builder' stage
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Set the new user
USER nextjs

EXPOSE 3000
ENV PORT 3000

# Start Next.js directly via its local binary. We intentionally do NOT use pnpm
# at runtime: corepack would re-resolve pnpm for the non-root user and download
# a newer pnpm that requires `node:sqlite` (Node 22+), crashing on Node 20.
CMD ["node_modules/.bin/next", "start"]
