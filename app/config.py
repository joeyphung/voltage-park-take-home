# config.py
from pydantic_settings import BaseSettings

# Define a configuration class that automatically loads settings
class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    upload_dir: str = "app/uploads"
    results_dir: str = "app/results"
    video_width: int = 1024
    video_height: int = 576
    video_frames: int = 25
    video_fps: int = 7
    decode_chunk_size: int = 8

    # Allows loading environment variables from a ".env" file
    class Config:
        env_file = ".env"

# Create a global settings object that can be imported anywhere
settings = Settings()