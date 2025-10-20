# main.py
import uuid
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from redis import Redis
from rq.job import Job
from prometheus_fastapi_instrumentator import Instrumentator
import aiofiles

from .config import settings
from .tasks import enqueue_video_task
from .logger_config import logger
from .metrics import (
    video_jobs_created,
)

# Create a new FastAPI web application instance.
app = FastAPI()

# Register Prometheus metrics endpoint
Instrumentator().instrument(app).expose(app)

# Ensure that the upload and results directories exist.
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.results_dir, exist_ok=True)

# Connect to Redis so we can check the job queue and status.
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)

@app.post("/generate")
async def generate(image: UploadFile = File(...)):
    """
    Upload an image and enqueue a video generation job.
    Returns the job ID for tracking.
    """
    task_id = str(uuid.uuid4())

    video_jobs_created.inc()  # Track job creation

    # Build paths for the input image and output video file.
    relative_input_path = os.path.join(settings.upload_dir, f"{task_id}_{image.filename}")
    relative_output_path = os.path.join(settings.results_dir, f"{task_id}.mp4")

    logger.info(f"Received upload: {image.filename} (task_id={task_id})")

    # Save the uploaded image file to disk using the relative path.
    # Use async file writing to avoid blocking
    async with aiofiles.open(relative_input_path, "wb") as f:
        content = await image.read()
        await f.write(content)
    logger.info(f"Saved uploaded image to {relative_input_path}")

    input_path = os.path.abspath(relative_input_path)
    output_path = os.path.abspath(relative_output_path)

    # Add (enqueue) the job to the Redis queue.
    # This means the task will be handled by a background worker, not the web server itself.
    job_id = enqueue_video_task(input_path, output_path)
    logger.info(f"Enqueued video generation job (job_id={job_id})")

    # Return the job ID to the client so it can check status later.
    return {"task_id": job_id, "status": "queued"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Check the status of a queued or running job.
    """
    try:
        # Fetch the job information from Redis.
        job = Job.fetch(job_id, connection=redis_conn)
        status = job.get_status()
        logger.info(f"Fetched job status (job_id={job_id}, status={status})")

        # Return current status and result (if finished).
        return {
            "task_id": job_id,
            "status": status,
            "result": str(job.result) if job.is_finished else None,
        }
    except Exception as e:

        # If the job doesn't exist or another error occurs.
        logger.warning(f"Status check failed for job_id={job_id}: {e}")
        return {"task_id": job_id, "status": "not_found"}

@app.get("/results/{job_id}")
async def get_result(job_id: str):
    """
    Download the video file once the job is complete.
    """
    try:
        # Retrieve job details from Redis
        # Extract the output path from the function arguments
        job = Job.fetch(job_id, connection=redis_conn)
        output_path = job.meta.get('output_path')

        # If the job has finished and the file exists, send it as a downloadable response.
        if job.is_finished and os.path.exists(output_path):
            logger.info(f"Job complete. Returning file for job_id={job_id}")
            return FileResponse(output_path, media_type="video/mp4", filename="generated_video.mp4")
        
        # If the job failed
        if job.is_failed:
            logger.warning(f"Result requested for failed job (job_id={job_id})")
            return {"error": "Job failed to generate video.", "status": "failed"}
        
        # If not finished or missing file, return an error message.
        logger.info(f"Job not finished or missing file (job_id={job_id})")
        return {"error": "Job not finished or file missing"}
    except Exception as e:

        # If job lookup failed
        logger.error(f"Error retrieving result for job_id={job_id}: {e}")
        return {"error": "Job not found"}

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    try:
        # Ping Redis to ensure it’s responding.
        redis_conn.ping()
        logger.info("Health check passed (Redis OK).")
        return {"status": "ok"}
    except Exception as e:
        # If Redis is unreachable, return unhealthy status.
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy"}