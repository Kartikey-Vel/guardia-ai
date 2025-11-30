# Guardia AI Deployment Guide

Complete guide for deploying Guardia AI in production and development environments.

---

## Prerequisites

### Hardware Requirements

#### **Minimum Configuration (CPU-only)**
- **CPU:** 8 vCPUs (Intel Xeon or AMD EPYC)
- **RAM:** 16GB
- **Storage:** 500GB SSD
- **Network:** 1 Gbps LAN
- **Cameras:** Up to 2 cameras at 10 FPS

#### **Recommended Configuration (GPU-accelerated)**
- **CPU:** 12+ vCPUs
- **GPU:** NVIDIA T4, RTX 4000, or Jetson Xavier NX
- **RAM:** 32GB
- **Storage:** 1TB NVMe SSD
- **Network:** 1 Gbps LAN (10 Gbps for 10+ cameras)
- **Cameras:** Up to 10 cameras at 10 FPS

#### **High-Performance Configuration**
- **CPU:** 24+ vCPUs
- **GPU:** NVIDIA A100, A10, or multiple T4s
- **RAM:** 64GB+
- **Storage:** 2TB+ NVMe SSD (RAID for redundancy)
- **Network:** 10 Gbps
- **Cameras:** 20+ cameras at 15-30 FPS

### Software Requirements

- **OS:** Ubuntu 22.04 LTS (recommended) or Ubuntu Server
- **Docker:** 24.0+ with Docker Compose v2
- **NVIDIA Driver:** 525+ (for GPU acceleration)
- **NVIDIA Container Toolkit:** For GPU support in containers
- **Git:** For cloning repository

---

## Installation Steps

### 1. **Prepare the System**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not included)
sudo apt install docker-compose-plugin

# For GPU support, install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU access (if applicable)
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 2. **Clone the Repository**

```bash
git clone https://github.com/codernotme/guardia.git
cd guardia
```

### 3. **Configure Cameras**

Edit `config/cameras.yaml`:

```bash
nano config/cameras.yaml
```

Add your camera configurations:

```yaml
cameras:
  - camera_id: cam_front
    name: Front Entrance
    url: rtsp://192.168.1.100/stream1
    username: admin
    password: your_password
    fps: 10
    enabled: true
    roi: null
```

### 4. **Configure Environment Variables**

Create `.env` file:

```bash
cp .env.example .env
nano .env
```

Key variables:

```env
# Redis
REDIS_URL=redis://redis:6379

# MinIO
MINIO_ROOT_USER=guardia
MINIO_ROOT_PASSWORD=change_this_secure_password

# PostgreSQL
POSTGRES_PASSWORD=change_this_db_password

# JWT Secret
JWT_SECRET=change_this_to_random_256bit_key

# Webhook (optional)
WEBHOOK_ENABLED=false
WEBHOOK_URL=

# Alert severity threshold
MIN_ALERT_SEVERITY=medium

# Privacy settings
FACE_BLUR_ENABLED=true
PRIVACY_MODE=true

# Logging
LOG_LEVEL=INFO
```

### 5. **Build and Start Services**

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 6. **Verify Deployment**

Check each service:

```bash
# Camera Ingest
curl http://localhost:8001/health

# Preprocessing
curl http://localhost:8002/health

# SkeleGNN
curl http://localhost:8003/health

# MotionStream
curl http://localhost:8004/health

# MoodTiny
curl http://localhost:8005/health

# FusionController
curl http://localhost:8006/health

# Alerts
curl http://localhost:8007/health

# API
curl http://localhost:8000/health

# Web Dashboard
# Open browser to http://localhost:3000
```

### 7. **Access the Dashboard**

Open your browser to: **http://localhost:3000**

Default credentials (change after first login):
- Username: `admin`
- Password: `guardia_admin`

---

## Production Deployment

### Security Hardening

1. **Change all default passwords**
   - MinIO root password
   - PostgreSQL password
   - JWT secret
   - Dashboard admin password

2. **Enable TLS/HTTPS**
   ```bash
   # Use reverse proxy (nginx/Traefik) with Let's Encrypt
   # See infra/docker/nginx.conf.example
   ```

3. **Configure firewall**
   ```bash
   # Only expose necessary ports
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

4. **Set up backup**
   ```bash
   # Backup SQLite database
   docker-compose exec fusion-controller sqlite3 /app/data/guardia.db .dump > backup.sql

   # Backup MinIO data
   docker-compose exec minio mc mirror minio/guardia-clips /backup/clips
   ```

### High Availability

For production, deploy with Kubernetes:

```bash
# Apply manifests
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/secrets.yaml
kubectl apply -f infra/k8s/deployments/
kubectl apply -f infra/k8s/services/

# Check deployment
kubectl get pods -n guardia
kubectl get svc -n guardia
```

### Monitoring Setup

1. **Access Prometheus**
   - URL: http://localhost:9090
   - Query metrics: `guardia_*`

2. **Access Grafana**
   - URL: http://localhost:3001
   - Username: `admin`
   - Password: `admin` (change on first login)
   - Import dashboard from `infra/docker/grafana-dashboard.json`

---

## GPU Acceleration

### Enable GPU for Model Services

Uncomment GPU sections in `docker-compose.yml`:

```yaml
skelegnn:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### TensorRT Optimization

For NVIDIA GPUs, convert models to TensorRT:

```bash
# Run conversion script
docker-compose exec skelegnn python /app/scripts/convert_to_tensorrt.py
```

---

## Scaling

### Horizontal Scaling

1. **Multiple Camera Ingest Instances**
   ```bash
   docker-compose up -d --scale camera-ingest=3
   ```

2. **Model Service Replicas**
   ```bash
   docker-compose up -d --scale skelegnn=2 --scale motionstream=2
   ```

### Load Balancing

Use nginx or HAProxy to distribute traffic:

```nginx
upstream guardia_api {
    server api:8000;
    server api:8000;  # Add more instances
}
```

---

## Troubleshooting

### Common Issues

#### 1. **Camera connection fails**
```bash
# Check camera URL
curl -v rtsp://camera_ip:554/stream

# Test with VLC
vlc rtsp://camera_ip:554/stream

# Check logs
docker-compose logs camera-ingest
```

#### 2. **High CPU usage**
```bash
# Check frame rates (reduce if needed)
# Edit config/cameras.yaml and set lower fps

# Check deduplication is enabled
docker-compose exec preprocessing curl http://localhost:8002/status
```

#### 3. **No events generated**
```bash
# Check model inference
docker-compose logs skelegnn
docker-compose logs motionstream
docker-compose logs moodtiny

# Check FusionController
docker-compose logs fusion-controller

# Verify min_confidence thresholds in rules
```

#### 4. **WebSocket connection refused**
```bash
# Check CORS settings
# Ensure web dashboard URL is allowed in alerts service

# Test WebSocket
wscat -c ws://localhost:8007/ws/alerts
```

### Debug Mode

Enable debug logging:

```bash
# Set in .env
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

---

## Maintenance

### Regular Tasks

1. **Database cleanup** (monthly)
   ```bash
   # Remove old events (>90 days)
   docker-compose exec fusion-controller sqlite3 /app/data/guardia.db \
     "DELETE FROM events WHERE created_at < datetime('now', '-90 days');"
   
   # Vacuum database
   docker-compose exec fusion-controller sqlite3 /app/data/guardia.db "VACUUM;"
   ```

2. **Clip retention** (weekly)
   ```bash
   # MinIO lifecycle policy handles this automatically
   # Verify policy
   docker-compose exec minio mc ilm ls minio/guardia-clips
   ```

3. **Model updates** (quarterly)
   ```bash
   # Download new models
   # Update weights in services/models/*/weights/
   
   # Restart model services
   docker-compose restart skelegnn motionstream moodtiny
   ```

4. **System updates** (monthly)
   ```bash
   # Update OS packages
   sudo apt update && sudo apt upgrade -y
   
   # Update Docker images
   docker-compose pull
   docker-compose up -d
   ```

---

## Backup & Restore

### Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/guardia/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Database
docker-compose exec -T fusion-controller sqlite3 /app/data/guardia.db .dump > $BACKUP_DIR/database.sql

# Configs
cp -r config $BACKUP_DIR/

# MinIO clips (optional, large)
# docker-compose exec minio mc mirror minio/guardia-clips $BACKUP_DIR/clips
```

### Restore

```bash
#!/bin/bash
# restore.sh

BACKUP_DIR="/backup/guardia/20231129"

# Stop services
docker-compose down

# Restore database
cat $BACKUP_DIR/database.sql | docker-compose exec -T fusion-controller sqlite3 /app/data/guardia.db

# Restore configs
cp -r $BACKUP_DIR/config ./

# Start services
docker-compose up -d
```

---

## Performance Tuning

### Optimize Frame Processing

```yaml
# config/cameras.yaml
fps: 5  # Reduce from 10 to 5 for 50% less load
```

### Model Quantization

Convert models to INT8 for 4x speedup:

```bash
python ml/experiments/quantize_model.py \
  --model skelegnn \
  --input weights/skelegnn.onnx \
  --output weights/skelegnn_int8.onnx
```

### Database Tuning

```sql
-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;

-- Increase cache size
PRAGMA cache_size=10000;
```

---

## Support & Resources

- **Documentation:** [docs/](../docs/)
- **GitHub Issues:** https://github.com/codernotme/guardia/issues
- **Community:** Join our Discord (link in README)
- **Security:** security@guardia-ai.example.com

---

**Guardia AI** - Secure deployment for proactive security intelligence.
