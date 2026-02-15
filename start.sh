#!/bin/bash

# Fail on error
set -e

# Setup Display
export DISPLAY=:99

# Start Xvfb
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1400x900x24 &

# Wait for Xvfb to be ready
until xset -q -display :99 > /dev/null 2>&1
do
    echo "Waiting for Xvfb..."
    sleep 1
done

# Start Fluxbox
echo "Starting Fluxbox..."
fluxbox &

# Start x11vnc
echo "Starting x11vnc..."
x11vnc -display :99 -forever -nopw -listen localhost -xkb &

# Start websockify as the primary web server on port 7860
# It will serve noVNC static files (including /health and /api/info)
# and proxy VNC traffic
echo "Starting websockify on 7860..."
websockify --web /opt/noVNC 7860 localhost:5900 &

# Start WitNote
echo "Starting WitNote..."
witnote --no-sandbox &

# Keep the script running
echo "Ready."
wait
