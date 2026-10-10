# Frontend Dockerfile for React + Vite application
FROM node:24-alpine AS builder

# Set working directory
WORKDIR /app

# Enable the package manager pinned in package.json
RUN corepack enable

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source files
COPY . .

# Accept build-time argument for API URL
ARG CAMPLY_API_URL
ENV CAMPLY_API_URL=$CAMPLY_API_URL

# Build the application
RUN pnpm run build

FROM nginx:alpine AS production

RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx.main.conf /etc/nginx/nginx.conf

RUN chown -R nginx:nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
