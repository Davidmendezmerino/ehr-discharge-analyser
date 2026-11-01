#!/bin/bash
set -e

echo "Starting EHR Discharge Analyser..."

# Start API in background
cd /app/api
uvicorn main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API to start..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "API is ready!"
        break
    fi
    sleep 1
done

# Start UI (Streamlit) on port 7860 (HF Spaces requirement)
cd /app/ui
API_URL=http://localhost:8000 \
    streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=7860 \
    --server.headless=true \
    --browser.gatherUsageStats=false

# If Streamlit exits, also stop the API
kill $API_PID
