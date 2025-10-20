# Stable Video Generation Service 🎥

This project is an asynchronous web service that generates a short video from a single input image using the Stability AI Stable Video Diffusion model. It's built with a robust, scalable architecture using FastAPI for the web server, Redis and RQ (Redis Queue) for background task management, and is fully containerized with Docker for easy deployment.

## Features ✨

- **Asynchronous Processing:** Upload an image and immediately get a task ID. The heavy video generation process runs in a background worker, so the API remains responsive.
- **GPU Accelerated:** The ML model is loaded onto a GPU within a dedicated worker service for high-performance inference.
- **Scalable Architecture:** The separation of the API and worker services allows them to be scaled independently.
- **Containerized:** The entire application stack (API, Worker, Redis) is managed with Docker and Docker Compose for consistent environments and simple deployment.
- **Observability:** Exposes a `/metrics` endpoint for Prometheus to scrape key application metrics (e.g., jobs created, failed, completed).
- **Configuration Management:** Easily configure application settings using environment variables or a `.env` file.

## Architecture Overview 🏗️

The service is composed of three main components that communicate via a Redis message broker.

1.  **FastAPI API Server:** The user-facing service that exposes endpoints to upload an image, check job status, and download the final video.
2.  **Redis:** Acts as the message broker for the task queue and stores job information.
3.  **RQ Worker:** A background service that listens for new jobs on the Redis queue. It pre-loads the Stable Video Diffusion model onto the GPU and performs the computationally intensive video generation task.

## Technology Stack 🛠️

- **Backend:** Python, FastAPI
- **Task Queue:** Redis, RQ (Redis Queue)
- **ML/AI:** PyTorch, Diffusers (Hugging Face)
- **Containerization:** Docker, Docker Compose
- **Observability:** Prometheus
- **Configuration:** Pydantic

## Getting Started

### Prerequisites

- **NVIDIA GPU:** A CUDA-enabled NVIDIA GPU is required for the worker.
- **NVIDIA Drivers:** The appropriate drivers for your GPU must be installed on the host machine.
- **Docker:** [Install Docker](https://docs.docker.com/get-docker/)
- **NVIDIA Container Toolkit:** This allows Docker containers to access the host's GPU. [Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2. **Configure the Application:**

    Configuration is managed using environment variables. You can set them using one of the following methods:

    **Method 1: Using a `.env` File (Recommended for Local Development)**

    Create a `.env` file in the project's root directory. The application will automatically load these variables on startup. This is the easiest way to get started.

    ```bash
    # .env
    # For Docker Compose, REDIS_HOST should match the service name in docker-compose.yml
    REDIS_HOST=redis
    REDIS_PORT=6379

    # Video Generation Settings
    VIDEO_WIDTH=1024
    VIDEO_HEIGHT=576
    VIDEO_FRAMES=25
    ```

    **Method 2: Setting Values Directly in `config.py`**

    Alternatively, you can define your configuration values directly in the `config.py` file.  
    This method is simple and works well for quick testing or environments where environment variables are not being used.

    ```python
    # config.py
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    VIDEO_WIDTH = 1024
    ```

3.  **Build and Run with Docker Compose:**
    This is the recommended method. It will build the images and start the API server, the RQ worker, and the Redis container.
    ```bash
    docker-compose up --build
    ```
    The API will be available at `http://localhost:8000`.

## API Endpoints 📖

The server provides the following endpoints:

| Method | Endpoint          | Description                                                               |
| :----- | :---------------- | :------------------------------------------------------------------------ |
| POST   | /generate         | Upload an image file to start a video generation job. Returns a `task_id`.  |
| GET    | /status/{task_id} | Check the status of a job (queued, started, finished, failed).            |
| GET    | /results/{task_id}| Once the job is finished, download the generated MP4 video from this URL. |
| GET    | /health           | A health check endpoint to verify that the API can connect to Redis.      |
| GET    | /metrics          | Exposes application metrics in a format that can be scraped by Prometheus. |

## Example API Response

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "queued"
}
```

## Check the Job Status

```bash
curl http://localhost:8000/status/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

## Download the Generated Result

```bash
curl -o output_video.mp4 http://localhost:8000/results/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

## Local Development (Without Docker Compose)

The `demo.sh` script provides a way to run the services locally for testing.  
This requires a Python virtual environment and manual startup of services.

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r app/requirements.txt
```

### 3. Run the demo script

```bash
chmod +x demo.sh
./demo.sh /path/to/your/image.jpg
```