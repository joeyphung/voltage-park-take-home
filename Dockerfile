# 1. Base Image: Start from an official NVIDIA image with CUDA and cuDNN
# This ensures all necessary GPU drivers and libraries are available.
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# 2. Setup Environment
# Set the working directory inside the container to /app
WORKDIR /code
# Add the user's local bin directory to the PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"
# Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure Python output is sent straight to the terminal without buffering
ENV PYTHONUNBUFFERED 1
# Tell Python to look for modules in the /app directory
ENV PYTHONPATH=/code

# 3. Install System Dependencies
RUN apt-get update && \
    apt-get install -y python3.10 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. Create non-root user (but don't switch to it yet)
RUN useradd -m appuser

# 5. Install Python Dependencies
# Copy requirements from the 'app' subdirectory first to leverage Docker's layer caching.
# If requirements.txt doesn't change, this layer won't be rebuilt.
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy Application Code
# Copy your local 'app' folder TO '/code/app' inside the container
COPY app /code/app

# 7. Set Correct Permissions as root
RUN chown -R appuser:appuser /code/app

# 8. NOW switch to the non-root user
USER appuser

# 9. Expose Port and Set Default Command
# The command to run when the container starts.
# This starts the FastAPI server using uvicorn.
# --host 0.0.0.0 makes it accessible from outside the container.
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]