# Guardia AI Enhanced System - Production Deployment Guide

## 🚀 Production Deployment Options

This guide covers multiple deployment strategies for the Guardia AI Enhanced System in production environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Configuration](#security-configuration)
- [Performance Optimization](#performance-optimization)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 100GB+ SSD for optimal performance
- **Network**: Stable internet connection for cloud features
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+), macOS, or Windows with WSL2

### Software Dependencies
- Docker and Docker Compose
- Git
- OpenSSL (for SSL certificates)

## Docker Deployment

### 1. Quick Production Setup

```bash
# Clone the repository
git clone https://github.com/your-org/guardia-ai.git
cd guardia-ai

# Copy and configure environment variables
cp .env.example .env
nano .env  # Edit with your production values

# Generate secure secret keys
openssl rand -hex 32  # Use this for SECRET_KEY

# Deploy with Docker Compose
docker-compose up -d

# Run system tests
./test_system.sh
```

### 2. Production Configuration

#### Environment Variables (.env)
```bash
# Core Settings
ENVIRONMENT=production
SECRET_KEY=your-generated-secure-key-here
DEBUG=false

# Database
MONGODB_URL=mongodb://username:password@mongodb:27017/guardia_ai
MONGODB_DATABASE=guardia_ai

# Security
JWT_EXPIRATION_MINUTES=60
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Notifications
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your-smtp-password

ENABLE_SMS_NOTIFICATIONS=true
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_FROM_NUMBER=+1234567890

# Storage
MAX_STORAGE_SIZE_MB=10000
RETAIN_MEDIA_DAYS=30
RETAIN_LOGS_DAYS=7
```

### 3. SSL/TLS Configuration

```bash
# Generate SSL certificates (using Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to project
mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*

# Enable nginx with SSL
docker-compose --profile with-nginx up -d
```

## Cloud Deployment

### AWS Deployment

#### 1. EC2 Instance Setup
```bash
# Launch EC2 instance (t3.large or larger)
# Ubuntu 20.04 LTS, 8GB+ RAM, 100GB+ storage

# Connect to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Clone and deploy
git clone https://github.com/your-org/guardia-ai.git
cd guardia-ai
cp .env.example .env
# Configure .env file
docker-compose up -d
```

#### 2. RDS MongoDB Atlas Setup
```bash
# MongoDB Atlas connection string
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/guardia_ai?retryWrites=true&w=majority
```

#### 3. S3 Storage Integration
```bash
# Configure AWS S3 for media storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-west-2
S3_BUCKET_NAME=guardia-ai-media
```

### Google Cloud Platform

#### 1. Compute Engine Setup
```bash
# Create VM instance
gcloud compute instances create guardia-ai \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=100GB \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud

# SSH and deploy
gcloud compute ssh guardia-ai
# Follow Docker deployment steps
```

#### 2. Cloud Storage Integration
```bash
# Configure Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCS_BUCKET_NAME=guardia-ai-storage
```

### Azure Deployment

#### 1. Container Instances
```yaml
# azure-container-instance.yaml
apiVersion: 2021-03-01
location: eastus
name: guardia-ai-container-group
properties:
  containers:
  - name: guardia-ai
    properties:
      image: your-registry/guardia-ai:latest
      resources:
        requests:
          cpu: 2.0
          memoryInGB: 4.0
      ports:
      - port: 8000
      environmentVariables:
      - name: ENVIRONMENT
        value: production
  osType: Linux
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 8000
```

## Security Configuration

### 1. Firewall Rules
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Fail2ban for brute force protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 2. Database Security
```bash
# MongoDB security
db.createUser({
  user: "guardia_admin",
  pwd: "secure_password",
  roles: [{ role: "readWrite", db: "guardia_ai" }]
})

# Enable authentication
# In /etc/mongod.conf:
security:
  authorization: enabled
```

### 3. Application Security
```bash
# Set secure environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_EXPIRATION_MINUTES=60

# Configure CORS properly
CORS_ORIGINS=https://yourdomain.com
```

## Performance Optimization

### 1. Resource Limits
```yaml
# docker-compose.production.yml
services:
  guardia-ai:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 2. Caching Configuration
```bash
# Redis for session caching
REDIS_URL=redis://redis:6379/0
SESSION_CACHE_TTL=3600
```

### 3. Database Optimization
```javascript
// MongoDB indexes
db.alerts.createIndex({ "user_id": 1, "created_at": -1 })
db.users.createIndex({ "email": 1 }, { unique: true })
db.family_members.createIndex({ "user_id": 1 })
```

## Monitoring and Maintenance

### 1. Health Monitoring
```bash
# Setup health check cron job
# /etc/cron.d/guardia-health
*/5 * * * * root /usr/local/bin/health_check.sh

# health_check.sh
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$response" != "200" ]; then
    systemctl restart docker-compose
    echo "$(date): Service restarted due to health check failure" >> /var/log/guardia-health.log
fi
```

### 2. Log Management
```bash
# Logrotate configuration
# /etc/logrotate.d/guardia-ai
/var/log/guardia-ai/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 guardia guardia
}
```

### 3. Resource Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Set up disk space alerts
# /etc/cron.daily/disk-space-check
#!/bin/bash
THRESHOLD=90
usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $usage -gt $THRESHOLD ]; then
    echo "Disk usage is ${usage}%" | mail -s "Disk Space Alert" admin@yourdomain.com
fi
```

## Backup and Recovery

### 1. Database Backup
```bash
#!/bin/bash
# backup_database.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/mongodb"
mkdir -p $BACKUP_DIR

# Create backup
mongodump --uri="mongodb://username:password@localhost:27017/guardia_ai" \
  --out=$BACKUP_DIR/backup_$DATE

# Compress backup
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/backup_$DATE
rm -rf $BACKUP_DIR/backup_$DATE

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR/backup_$DATE.tar.gz s3://your-backup-bucket/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete
```

### 2. Media Backup
```bash
#!/bin/bash
# backup_media.sh
MEDIA_DIR="/app/storage"
BACKUP_DIR="/backup/media"
DATE=$(date +%Y%m%d)

# Sync media files
rsync -av --delete $MEDIA_DIR/ $BACKUP_DIR/current/

# Create daily snapshot
cp -al $BACKUP_DIR/current $BACKUP_DIR/snapshot_$DATE

# Upload to cloud
aws s3 sync $BACKUP_DIR/snapshot_$DATE s3://your-backup-bucket/media/snapshot_$DATE/
```

### 3. Automated Backup Schedule
```bash
# /etc/cron.d/guardia-backup
# Database backup every 6 hours
0 */6 * * * root /usr/local/bin/backup_database.sh

# Media backup daily at 2 AM
0 2 * * * root /usr/local/bin/backup_media.sh
```

## Scaling Considerations

### 1. Horizontal Scaling
```yaml
# docker-compose.scale.yml
services:
  guardia-ai:
    deploy:
      replicas: 3
  
  nginx:
    depends_on:
      - guardia-ai
    # Load balancer configuration
```

### 2. Database Scaling
```bash
# MongoDB replica set configuration
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
})
```

## Troubleshooting

### Common Issues
1. **High CPU usage**: Check detection thresholds and frame processing settings
2. **Memory leaks**: Monitor container resources and restart if necessary
3. **Database connection issues**: Verify MongoDB credentials and network connectivity
4. **Camera access problems**: Check device permissions and video source URLs

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# View real-time logs
docker-compose logs -f guardia-ai
```

## Support and Updates

### Automated Updates
```bash
#!/bin/bash
# update_system.sh
cd /opt/guardia-ai
git pull origin main
docker-compose build --no-cache
docker-compose up -d
./test_system.sh
```

### Health Notifications
```bash
# Setup email alerts for system issues
ALERT_EMAIL=admin@yourdomain.com
```

For additional support, please refer to:
- [README_ENHANCED.md](README_ENHANCED.md) for detailed setup instructions
- [API Documentation](http://localhost:8000/docs) for integration details
- GitHub Issues for bug reports and feature requests
