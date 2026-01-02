# Build stage
FROM node:20-slim AS build
WORKDIR /app

# Ensure we have the environment variable during build if possible
# Note: Railway requires this to be set in the 'Variables' tab to be available here
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:20-slim
WORKDIR /app
# Install serve globally in the final stage
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE $PORT
# Use a simple shell command to start serve on the Railway port
CMD serve -s dist -l $PORT
