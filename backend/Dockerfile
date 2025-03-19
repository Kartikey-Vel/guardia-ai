FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for OpenCV, TensorFlow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "src.main"]
