# Build stage
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app
# Install a specific version of serve for stability
RUN npm install -g serve@14.2.3
# Copy the entire dist folder instead of just contents
COPY --from=build /app/dist ./dist
EXPOSE $PORT
# Explicitly serve the dist folder with single-page-app routing
CMD ["sh", "-c", "serve -s dist -l $PORT"]
