# Build stage
ARG BASE_REGISTRY=fmk-prod.nexus-ci.onefiserv.net
ARG BASE_IMAGE=fmk/node/node20:FMK-24-12-17
FROM $BASE_REGISTRY/$BASE_IMAGE

# NPM auth token for private registry
ARG NPM_AUTH_TOKEN

# Switch to root to install global packages
USER root

# Install pnpm and serve globally
RUN npm install -g pnpm@10.24.0 serve

# Set working directory
WORKDIR /app

# Copy package files and .npmrc
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./

# Install dependencies with auth token
RUN NPM_AUTH_TOKEN=${NPM_AUTH_TOKEN} pnpm install --frozen-lockfile

# Remove .npmrc after install (security: don't keep credentials in image)
RUN rm -f .npmrc

# Copy source files
COPY . .

# Build the project
RUN pnpm run build

# Expose port
EXPOSE 8080

# Start the server
CMD ["serve", "-s", "./assets", "-p", "8080", "--cors"]
