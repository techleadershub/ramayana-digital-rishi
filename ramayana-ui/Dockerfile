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
# Use npx directly in the CMD to avoid global install issues, 
# and explicitly bind to 0.0.0.0
COPY --from=build /app/dist ./dist
EXPOSE $PORT
CMD ["npx", "-y", "serve", "-s", "dist", "-l", "0.0.0.0:$PORT"]
