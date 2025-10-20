#metrics.py
from prometheus_client import Counter, Gauge, Histogram

# Custom metrics for video jobs
video_jobs_created = Counter("video_jobs_created_total", "Number of video generation jobs created.")
video_jobs_completed = Counter("video_jobs_completed_total", "Number of completed jobs.")
video_jobs_failed = Counter("video_jobs_failed_total", "Number of failed jobs.")
video_jobs_in_progress = Gauge("video_jobs_in_progress", "Jobs currently running.")
video_job_duration = Histogram("video_job_duration_seconds", "Duration of video jobs (s).")