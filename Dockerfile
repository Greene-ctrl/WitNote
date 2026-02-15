# Use Ubuntu 22.04 as base
FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    xvfb \
    x11vnc \
    fluxbox \
    websockify \
    nginx \
    python3-pip \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    x11-xserver-utils \
    wget \
    ca-certificates \
    gnupg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install FastAPI and Uvicorn for health/info API
RUN pip3 install fastapi uvicorn

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Setup noVNC
RUN mkdir -p /opt/noVNC && \
    git clone https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html

# Create a non-root user
RUN useradd -m -u 1000 user
ENV HOME=/home/user
WORKDIR /home/user

# Create vault directory
RUN mkdir -p /app/vault && chown user:user /app/vault && chmod 777 /app/vault
ENV VAULT_ROOT=/app/vault

# Clone and build the application from the official repository
# This avoids git storage and binary file issues in the Hugging Face Space repository
RUN git clone https://github.com/hooosberg/WitNote.git /home/user/app-source
WORKDIR /home/user/app-source
RUN npm install
# Build the Linux package
RUN npm run build:linux

# Install the built .deb package as root
USER root
# Find the .deb file and install it
RUN apt-get update && apt-get install -y ./release/*.deb || apt-get install -f -y

# Copy configuration and startup files from the build context
WORKDIR /home/user
COPY --chown=user:user api_server.py .
COPY --chown=user:user nginx.conf .
COPY --chown=user:user start.sh .
RUN chmod +x start.sh

# HF Spaces requirements
USER user
ENV DISPLAY=:99
EXPOSE 7860

# Launch using the startup script
CMD ["/home/user/start.sh"]
