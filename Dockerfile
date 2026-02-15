# Stage 1: Build the application
FROM node:20-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Copy local source code instead of cloning
COPY . .
RUN npm install
RUN npm run build:linux

# Stage 2: Runtime environment
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    websockify \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    x11-xserver-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Setup noVNC
RUN mkdir -p /opt/noVNC && \
    git clone --depth 1 https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone --depth 1 https://github.com/novnc/websockify /opt/noVNC/utils/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html

# Create a non-root user
RUN useradd -m -u 1000 user
WORKDIR /home/user

# Copy the built package from the builder stage
COPY --from=builder /app/release/*.deb /tmp/package.deb

# Install the application
RUN apt-get update && apt-get install -y /tmp/package.deb && rm /tmp/package.deb && rm -rf /var/lib/apt/lists/*

# Setup health check and static API info for websockify
RUN mkdir -p /opt/noVNC/api && \
    echo "ok" > /opt/noVNC/health && \
    echo '{"app":"WitNote","version":"1.3.3","mode":"VNC"}' > /opt/noVNC/api/info

# Setup permissions for non-root execution
RUN mkdir -p /home/user/.config && chown -R user:user /home/user

# Copy startup script from the build context
COPY start.sh /home/user/start.sh
RUN chmod +x /home/user/start.sh

USER user
EXPOSE 7860

CMD ["/home/user/start.sh"]
