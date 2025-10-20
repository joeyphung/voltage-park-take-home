# worker.py
from redis import Redis
from rq import Queue, SimpleWorker
import torch # Needed for the StableVideoDiffusionPipeline
from diffusers import StableVideoDiffusionPipeline
from .config import settings
from .logger_config import logger

# This class defines a custom RQ worker that inherits from SimpleWorker.
# SimpleWorker is used to prevent GPU memory errors by running jobs
# in the main process instead of forking a new one for each task.
# This custom class extends that behavior by injecting the pre-loaded ML model
# into each job's keyword arguments, making the model accessible to the task function.
class CustomWorker(SimpleWorker):
    def __init__(self, *args, **kwargs):
        # Pop the custom 'model' argument before calling the parent constructor
        self.model = kwargs.pop('model')
        super().__init__(*args, **kwargs)

    def perform_job(self, job, *args, **kwargs):
        """
        This method is an RQ hook that runs just before a job is executed.
        It injects the pre-loaded ML model from the worker (self.model) into the
        job's keyword arguments. This makes the model efficiently available to the
        task function without reloading it from disk for every job.
        """
        job.kwargs['model'] = self.model
        return super().perform_job(job, *args, **kwargs)

# Define which queue(s) this worker should listen to.
# In our case, there's only one queue called "video-tasks".
listen = ["video-tasks"]

# Connect to Redis using the same configuration as the web app.
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port)

# Load the model onto the worker
def load_model():
    logger.info("Loading Stable Video Diffusion model...")

    # Load a pre-trained video diffusion model from Hugging Face.
    # "stabilityai/stable-video-diffusion-img2vid-xt" is the model name.
    # Use 16 bit floating point
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt",
        variant="fp16"
    )

    # Move the model to the GPU for faster processing.
    pipe.to("cuda")

    logger.info("Model loaded successfully onto GPU.")
    return pipe

# Entry point for the worker process.
# This file should be run in a separate terminal using:
# python worker.py
if __name__ == "__main__":
    logger.info("Starting RQ worker...")

    # Load the model 
    video_pipeline = load_model()

    # Create a list of Queue objects, ensuring each has a connection.
    queues = [Queue(name, connection=redis_conn) for name in listen]

    # Create a worker that listens to the "video-tasks" queue.
    worker = CustomWorker(
        queues,
        connection=redis_conn,
        model=video_pipeline
    )
    logger.info(f"Worker initialized. Listening on queues: {listen}")

    # Start the worker loop — it will continuously check Redis for new jobs.
    try:
        worker.work()
    except Exception as e:
        logger.exception(f"Worker encountered an error: {e}")
    finally:
        logger.info("Worker shutting down.")