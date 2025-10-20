# tasks.py
from redis import Redis
from rq import Queue
from rq.job import Retry
from .config import settings
from .video_gen import create_video
from .logger_config import logger

# Connect to Redis database where job queues are stored.
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)

# Create a queue object tied to Redis.
# The name "video-tasks" must match what the worker listens to.
# Create a queue (you can have multiple queues for different priorities)
queue = Queue("video-tasks", connection=redis_conn)

def enqueue_video_task(image_path: str, output_path: str):
    """
    Enqueue a video generation job to be processed by an RQ worker.
    """

    logger.info(f"Queueing video generation job for image: {image_path}")
    try:
        # Add the `create_video` function to the Redis queue for background execution.
        # retry=3 means if it fails, it will retry up to 3 times automatically.
        job = queue.enqueue(create_video, image_path, output_path, retry=Retry(max=3))

        # Save the output path for main.py
        job.meta['output_path'] = output_path
        job.save_meta()

        logger.info(f"Job queued successfully (job_id={job.id})")

        # Return the job ID so the caller can track its progress.
        return job.id
        
    except Exception as e:
        logger.exception(f"Failed to enqueue job for {image_path}: {e}")
        raise