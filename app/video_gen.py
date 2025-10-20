# video_gen.py
import time
import os
from diffusers.utils import load_image, export_to_video
from .config import settings
from .logger_config import logger
from .metrics import (
    video_jobs_completed,
    video_jobs_failed,
    video_jobs_in_progress,
    video_job_duration,
)

def create_video(image_path: str, output_path: str, **kwargs):
    """
    Generates a video from an input image and saves it.
    """
    start_time = time.time()
    video_jobs_in_progress.inc()
    logger.info(f"Starting video generation for {image_path}")

    try:
        # Get the model passed in from the custom worker
        pipe = kwargs.get('model')
        if pipe is None:
            raise ValueError("Model not provided to the video generation task.")

        # Load the input image from the given file path and resize it for the model
        image = load_image(image_path).resize((settings.video_width, settings.video_height))

        # Generate frames (individual images) for the video from the input image.
        # num_frames = number of frames to generate.
        # decode_chunk_size controls how many frames are processed at a time (to save memory).
        # Expects a batch and outputs a batch so index into the first video of the batch
        frames = pipe(
            image, 
            num_frames=settings.video_frames, 
            decode_chunk_size=settings.decode_chunk_size
        ).frames[0]

        # Export all generated frames as a video file to the specified output path.
        # fps (frames per second) controls how fast the video plays.
        export_to_video(frames, output_path, fps=settings.video_fps)

        # Clean up the original uploaded image file to save disk space.
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Cleaned up source file: {image_path}")

        video_jobs_completed.inc()
        logger.info(f"Video generation complete: {output_path}")
    except Exception as e:
        video_jobs_failed.inc()
        logger.error(f"Video generation failed for {image_path}: {e}")
        raise
    finally:
        # The decrements still belong here to run regardless of outcome
        video_jobs_in_progress.dec()
        video_job_duration.observe(time.time() - start_time)