# Use the official Node.js 20 Alpine image as a base
FROM node:20-alpine

# Install pnpm globally
RUN npm install -g pnpm

# Set the working directory in the container
WORKDIR /app

# Copy package.json and the lockfile to leverage Docker's layer caching.
# This step is crucial and fixes the error you're seeing.
COPY package.json pnpm-lock.yaml ./

# Install dependencies using the frozen lockfile for consistency
RUN pnpm install --frozen-lockfile

# Copy the rest of the application's source code into the container
COPY . .

# Expose the port the Next.js development server runs on
EXPOSE 3000

# The default command to start the development server
CMD ["pnpm", "dev"]