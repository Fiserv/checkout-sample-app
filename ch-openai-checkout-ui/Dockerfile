# Build stage
FROM node:20-alpine

# Install pnpm and serve globally
RUN npm install -g pnpm@10.24.0 serve

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source files
COPY . .

# Build the project
RUN pnpm run build

# Expose port
EXPOSE 8088

# Start the server
CMD ["serve", "-s", "./assets", "-p", "8088", "--cors"]
