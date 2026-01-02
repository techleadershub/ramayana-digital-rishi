# Build stage
FROM node:20-slim AS build
WORKDIR /app

# Accept VITE_API_URL as a build argument
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm install
COPY . .
# The env var must be present during this step
RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app
COPY --from=build /app/dist ./dist
EXPOSE $PORT
CMD npx -y serve -s dist -l $PORT
