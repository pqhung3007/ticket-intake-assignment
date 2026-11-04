# syntax=docker/dockerfile:1
# Frontend image for local development (Vite dev server with hot reload).
# In production the built SPA is served by the backend (see the repository-root Dockerfile).

FROM node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0"]
