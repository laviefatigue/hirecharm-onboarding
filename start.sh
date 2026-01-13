#!/bin/sh

# Start FastAPI backend in background
echo "Starting FastAPI backend..."
cd /app/api
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Wait for API to be ready
echo "Waiting for API to be ready..."
sleep 3

# Start nginx in foreground
echo "Starting nginx..."
nginx -g 'daemon off;'
