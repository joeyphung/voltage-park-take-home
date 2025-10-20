#!/bin/bash

# A script to run the full video generation service and test it.
#
# Prerequisites:
#   - Docker is installed and the Docker Desktop application is running.
#   - A Python virtual environment named 'venv' exists with all requirements installed.
#   - 'jq' is installed for parsing JSON (e.g., 'sudo apt-get install jq' on Linux
#     or 'brew install jq' on macOS, or 'winget install jqlang.jq' on Windows).
#
# Usage:
#   Make the script executable: chmod +x run_demo.sh
#   Run it with the path to your image: ./run_demo.sh /path/to/your/image.png

# This ensures all other paths are correct, regardless of where the script is called from.
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# --- Configuration ---
IMAGE_PATH=$1
REDIS_CONTAINER_NAME="redis-video-service"
APP_DIR="$SCRIPT_DIR/app"

# --- Script Functions ---

# Function to handle cleanup when the script exits
cleanup() {
    echo ""
    echo "--- 🧹 Cleaning up resources ---"

    echo "Sending shutdown signals to services..."
    # Use pkill -f to find and kill processes by their command string.
    # This is the most reliable method.
    pkill -f "uvicorn app.main:app"
    pkill -f "python -m app.worker"

    # Give the OS a few seconds to process the signals and terminate the processes.
    echo "Waiting for services to shut down..."
    sleep 3

    echo "✅ Services shut down."

    # NOW it is safe to stop and remove the Redis container
    if [ "$(docker ps -a -q -f name=$REDIS_CONTAINER_NAME)" ]; then
        echo "Stopping and removing Redis container..."
        docker stop "$REDIS_CONTAINER_NAME" > /dev/null
        docker rm "$REDIS_CONTAINER_NAME" > /dev/null
    fi

    echo "Cleanup complete."
}

# Trap the EXIT signal to ensure the cleanup function is always called
trap cleanup EXIT

# --- Main Script ---

# Check if an image path was provided
if [ -z "$IMAGE_PATH" ]; then
    echo "❌ Error: Please provide the path to an image as the first argument."
    echo "Usage: ./run_demo.sh /path/to/your/image.png"
    exit 1
fi

# Check if the image file exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Error: Image file not found at '$IMAGE_PATH'"
    exit 1
fi

echo "--- 🚀 Starting Video Generation Service ---"

# 1. Start Redis with Docker
echo "Step 1: Starting Redis container..."
docker run -d --rm --name $REDIS_CONTAINER_NAME -p 6379:6379 redis > /dev/null
echo "✅ Redis container '$REDIS_CONTAINER_NAME' started."

# Wait for Redis to be ready
echo "Waiting for Redis to start..."
until docker exec $REDIS_CONTAINER_NAME redis-cli ping &>/dev/null; do
    echo -n "."
    sleep 1
done
echo ""
echo "✅ Redis is ready."

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    VENV_ACTIVATE="$SCRIPT_DIR/venv/Scripts/activate"
else
    VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"
fi

# 2. Start the RQ worker using its absolute path for reliability
echo "Step 2: Starting RQ worker in the background..."
LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu $SCRIPT_DIR/venv/bin/python -m app.worker &
WORKER_PID=$!
echo "✅ Worker started with PID: $WORKER_PID"

# 3. Start the FastAPI server using its absolute path for reliability
echo "Step 3: Starting FastAPI server in the background..."
$SCRIPT_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
echo "✅ API server started with PID: $API_PID"

# Wait for the API server to be healthy
echo "⏳ Waiting for API server to be ready..."
until curl -s -f http://localhost:8000/health > /dev/null; do
    echo -n "."
    sleep 1
done
echo ""
echo "✅ API server is ready."

echo ""
echo "--- 📤 Submitting Video Generation Job ---"

# 4. Submit the image to the /generate endpoint
echo "Step 4: Uploading '$IMAGE_PATH' to the API..."
RESPONSE=$(curl -s -X POST -F "image=@$IMAGE_PATH" http://localhost:8000/generate)
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

if [ "$TASK_ID" == "null" ] || [ -z "$TASK_ID" ]; then
    echo "❌ Error: Failed to submit job. Server response:"
    echo "$RESPONSE"
    exit 1
fi
echo "✅ Job submitted successfully. Task ID: $TASK_ID"

# 5. Poll the /status endpoint until the job is finished or fails
echo "Step 5: Polling job status (will check every 5 seconds)..."
while true; do
    STATUS_RESPONSE=$(curl -s http://localhost:8000/status/$TASK_ID)
    JOB_STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    echo "Current job status: $JOB_STATUS"

    if [ "$JOB_STATUS" == "finished" ]; then
        echo "🎉 Job finished successfully!"
        break
    elif [ "$JOB_STATUS" == "failed" ]; then
        echo "❌ Error: Job failed."
        exit 1
    fi
    
    sleep 5
done

# 6. Download the final video from the /results endpoint
echo "Step 6: Downloading the resulting video..."
curl -s -o generated_video.mp4 http://localhost:8000/results/$TASK_ID

if [ -s "generated_video.mp4" ]; then
    echo "✅ Video downloaded successfully as 'generated_video.mp4'."
else
    echo "❌ Error: Failed to download the video file."
fi

echo ""
echo "--- Demo complete ---"
exit 0