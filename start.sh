#!/bin/bash

# Fail on error
set -e

# Setup Display
export DISPLAY=:99
export XDG_RUNTIME_DIR=/tmp/runtime-user
mkdir -p $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR

# Nginx temp dirs
mkdir -p /tmp/nginx/client_body
mkdir -p /tmp/nginx/proxy_temp
mkdir -p /tmp/nginx/fastcgi_temp
mkdir -p /tmp/nginx/uwsgi_temp
mkdir -p /tmp/nginx/scgi_temp

# Start Xvfb
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1400x900x24 &

# Wait for Xvfb to be ready
until xset -q -display :99 > /dev/null 2>&1
do
    echo "Waiting for Xvfb..."
    sleep 1
done

# Start Fluxbox (Window Manager)
echo "Starting Fluxbox..."
fluxbox &

# Start x11vnc
echo "Starting x11vnc..."
x11vnc -display :99 -forever -nopw -listen localhost -xkb &

# Start noVNC proxy on 6080
echo "Starting noVNC..."
/opt/noVNC/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

# Start API server on 7861
echo "Starting API server..."
python3 api_server.py &

# Start Nginx on 7860
echo "Starting Nginx..."
nginx -c $(pwd)/nginx.conf &

# Start WitNote
# Use --no-sandbox because we are running in a container
echo "Starting WitNote..."
witnote --no-sandbox &

# Keep the script running
echo "Environment is ready."
wait
