
# Use official Python 3.10 image for AI/ML compatibility
FROM python:3.10-slim

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libegl1 \
    libgl1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set Python path to include the project root
ENV PYTHONPATH=/app

# Set environment variables for headless mode
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=offscreen
ENV DEBIAN_FRONTEND=noninteractive

# Expose default webcam and Flask ports (if used)
EXPOSE 5000

# Default command (can be overridden)
CMD ["python", "/guardia_ai/main.py"]
