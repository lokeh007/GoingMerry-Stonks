# Multi-stage Dockerfile for React Frontend with Testing
# Production-optimized with nginx and test validation

# ========================================
# Stage 1: Test and Build
# ========================================
FROM node:18-alpine as test

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including dev dependencies for testing)
RUN npm ci

# Copy application source
COPY . .

# Run linting
RUN echo "Running linting..." && \
    npm run lint || (echo "❌ Linting failed" && exit 1) && \
    echo "✅ Linting passed"

# Run type checking
RUN echo "Running type checking..." && \
    npm run type-check || (echo "❌ Type checking failed" && exit 1) && \
    echo "✅ Type checking passed"

# Run tests with coverage
RUN echo "Running test suite..." && \
    npm run test:coverage || (echo "❌ Tests failed or coverage below 80%" && exit 1) && \
    echo "✅ All tests passed with adequate coverage"

# Build the application
RUN echo "Building production bundle..." && \
    npm run build && \
    echo "✅ Build successful"

# ========================================
# Stage 2: Production with nginx
# ========================================
FROM nginx:1.25-alpine

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application from test stage (only if tests passed!)
COPY --from=test /app/build /usr/share/nginx/html

# Create nginx cache directories
RUN mkdir -p /var/cache/nginx/client_temp && \
    mkdir -p /var/cache/nginx/proxy_temp && \
    mkdir -p /var/cache/nginx/fastcgi_temp && \
    mkdir -p /var/cache/nginx/uwsgi_temp && \
    mkdir -p /var/cache/nginx/scgi_temp

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

# Switch to non-root user
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

USER nginx

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# Build metadata
LABEL maintainer="GoingMerry-Stonks Team"
LABEL version="1.0.0"
LABEL description="React frontend for stock and options analysis (tested and production-ready)"
