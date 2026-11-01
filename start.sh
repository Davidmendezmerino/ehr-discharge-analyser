#!/bin/bash
set -e

echo "Starting EHR Discharge Analyser..."

# Start API in background
cd /app/api
uvicorn main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
UI_PID=
cleanup() {
    if [ -n "$UI_PID" ]; then
        kill "$UI_PID" 2>/dev/null || true
        wait "$UI_PID" 2>/dev/null || true
    fi
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Wait for API to be ready
echo "Waiting for API to start..."
API_READY=0
for i in $(seq 1 30); do
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "API exited before it became ready." >&2
        exit 1
    fi
    if python -c 'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=1).close()' > /dev/null 2>&1; then
        echo "API is ready!"
        API_READY=1
        break
    fi
    sleep 1
done
if [ "$API_READY" -ne 1 ]; then
    echo "API did not become ready within the startup window." >&2
    exit 1
fi

# Start UI (Streamlit) on port 7860 (HF Spaces requirement)
cd /app/ui
API_URL=http://localhost:8000 \
    streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=7860 \
    --server.headless=true \
    --browser.gatherUsageStats=false &
UI_PID=$!
wait "$UI_PID"

# The EXIT trap stops the API even if Streamlit exits with an error.
