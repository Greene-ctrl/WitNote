# Stage 1: Build the frontend
FROM node:20-slim AS build-stage
WORKDIR /app
COPY package.json ./
# Use npm install
RUN npm install
COPY . .
# Set IS_WEB=true for the build
ENV IS_WEB=true
RUN npm run build:web

# Stage 2: Serve with FastAPI
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install fastapi uvicorn requests pydantic

# Copy built frontend
COPY --from=build-stage /app/dist /app/dist

# Copy backend
COPY server.py /app/server.py
# web-bridge.js is already in /app/dist because it was in public/ during build

# Create vault directory
RUN mkdir -p /app/vault && chmod 777 /app/vault

# Non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    VAULT_ROOT=/app/vault

WORKDIR /app

# Start the server
CMD ["python", "server.py"]
