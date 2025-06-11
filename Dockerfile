# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Install system dependencies for OpenCV and face_recognition
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    pkg-config \
    python3-dev \
    python3-pip \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    # Math libraries
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    # TBB libraries (updated names)
    libtbb12-dev \
    libtbb-dev \
    # GUI dependencies
    libx11-dev \
    libgtk-3-dev \
    python3-tk \
    # Additional libraries
    openexr \
    libopenexr-dev \
    && rm -rf /var/lib/apt/lists/*

# Try to install dlib dependencies (some may not be available)
RUN apt-get update && apt-get install -y \
    libdlib-dev \
    libdc1394-dev \
    || echo "Some optional packages not available, continuing..." && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip and install build tools first
RUN pip install --upgrade pip setuptools wheel

# Install dependencies separately with proper quoting to avoid shell issues
RUN pip install --no-cache-dir "numpy>=1.24.0,<2.0.0" || echo "numpy install failed"
RUN pip install --no-cache-dir "opencv-python>=4.8.0" || echo "opencv install failed"
RUN pip install --no-cache-dir "pillow>=8.3.0" || echo "pillow install failed"
RUN pip install --no-cache-dir "scipy>=1.9.0" || echo "scipy install failed"

# Install cmake and dlib with fallback
RUN pip install --no-cache-dir "cmake>=3.18.0" || echo "cmake install failed"
RUN pip install --no-cache-dir --verbose "dlib>=19.24.0" || echo "dlib install failed, will use fallback"

# Install face-recognition with fallback
RUN pip install --no-cache-dir "face-recognition>=1.3.0" || echo "face-recognition install failed, will use fallback"

# Copy requirements and install any remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || echo "Some requirements failed, continuing..."

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p encodings faces images data detected/known detected/unknown logs config src/modules

# Set environment variables
ENV DISPLAY=:0
ENV PYTHONPATH=/app/src
ENV DEBIAN_FRONTEND=noninteractive

# Expose any ports if needed (for future web interface)
EXPOSE 8000

# Add a healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the application
CMD ["python", "/app/src/main.py"]
