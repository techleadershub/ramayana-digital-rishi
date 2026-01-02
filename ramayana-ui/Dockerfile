# Build stage
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
# Double check the build exists
RUN ls -la /app/dist

# Production stage
FROM node:20-slim
WORKDIR /app
RUN npm install -g serve
# Copy ALL contents from the build's dist folder directly into /app
COPY --from=build /app/dist .
# Verify the files are in the final image
RUN ls -la /app

EXPOSE $PORT
# Serve the current directory (.) as a single-page app
CMD ["sh", "-c", "serve -s . -l $PORT"]
