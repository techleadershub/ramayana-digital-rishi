# Build stage
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Build with environment variables available at build time
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app
# Install a specific version of serve for stability
RUN npm install -g serve@14.2.3
# Copy the entire dist folder instead of just contents
COPY --from=build /app/dist ./dist
# Use PORT environment variable, default to 3000 if not set
ENV PORT=3000
EXPOSE $PORT
# Explicitly serve the dist folder with single-page-app routing
CMD ["sh", "-c", "serve -s dist -l ${PORT:-3000}"]
