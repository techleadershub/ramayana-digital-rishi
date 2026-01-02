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
COPY --from=build /app/dist ./dist
# Railway provides $PORT
EXPOSE $PORT
# Use shell form to ensure $PORT is correctly expanded by the environment
CMD npx -y serve -s dist -l $PORT
