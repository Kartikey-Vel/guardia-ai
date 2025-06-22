#!/bin/bash

# Guardia AI Enhanced System - Complete Setup Script
# This script helps users configure all credentials and settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Guardia AI Enhanced System - Complete Setup${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    echo -ne "${YELLOW}$prompt${NC}"
    if [ -n "$default" ]; then
        echo -ne " ${BLUE}(default: $default)${NC}"
    fi
    echo -ne ": "
    
    read input
    if [ -z "$input" ] && [ -n "$default" ]; then
        input="$default"
    fi
    
    eval "$var_name='$input'"
}

# Function to prompt for secret input
prompt_secret() {
    local prompt="$1"
    local var_name="$2"
    
    echo -ne "${YELLOW}$prompt${NC}: "
    read -s input
    echo
    eval "$var_name='$input'"
}

# Check if .env exists
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file found${NC}"
    echo -ne "${YELLOW}Do you want to reconfigure credentials? (y/N)${NC}: "
    read reconfigure
    if [ "$reconfigure" != "y" ] && [ "$reconfigure" != "Y" ]; then
        echo "Using existing configuration. Run 'python validate_config.py' to validate."
        exit 0
    fi
else
    echo -e "${YELLOW}📝 Creating new .env configuration${NC}"
    cp .env.example .env
fi

echo
echo -e "${BLUE}🔧 Core Application Settings${NC}"
echo "================================"

prompt_with_default "Environment (development/staging/production)" "development" ENVIRONMENT
prompt_with_default "Debug mode (true/false)" "true" DEBUG
prompt_with_default "Host address" "0.0.0.0" HOST
prompt_with_default "Port number" "8000" PORT

echo
echo -e "${BLUE}🔐 Security Settings${NC}"
echo "===================="

if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${RED}⚠️  Production environment detected!${NC}"
    echo "Please generate a secure secret key:"
    echo "Run: openssl rand -hex 32"
    echo
    prompt_secret "Enter your SECRET_KEY (32+ characters)" SECRET_KEY
    
    if [ ${#SECRET_KEY} -lt 32 ]; then
        echo -e "${RED}❌ SECRET_KEY must be at least 32 characters!${NC}"
        exit 1
    fi
else
    SECRET_KEY="dev-secret-key-change-for-production-use-guardia-ai-2025"
    echo -e "${GREEN}Using development SECRET_KEY${NC}"
fi

prompt_with_default "JWT expiration (minutes)" "1440" JWT_EXPIRATION

echo
echo -e "${BLUE}💾 Database Configuration${NC}"
echo "=========================="

echo "Current MongoDB URL: mongodb+srv://aryanbajpai2411:ESOS5bbK4XLq2mZV@gaurdia-ai-vi-main.drm97zq.mongodb.net/..."
echo -ne "${YELLOW}Use existing MongoDB Atlas connection? (Y/n)${NC}: "
read use_existing_db

if [ "$use_existing_db" = "n" ] || [ "$use_existing_db" = "N" ]; then
    prompt_with_default "MongoDB URL" "" MONGODB_URL
    prompt_with_default "Database name" "guardia_ai_db" MONGODB_DATABASE
else
    MONGODB_URL="mongodb+srv://aryanbajpai2411:ESOS5bbK4XLq2mZV@gaurdia-ai-vi-main.drm97zq.mongodb.net/?retryWrites=true&w=majority&appName=gaurdia-ai-vi-main"
    MONGODB_DATABASE="guardia_ai_db"
    echo -e "${GREEN}Using existing MongoDB Atlas connection${NC}"
fi

echo
echo -e "${BLUE}☁️  Google Cloud Configuration${NC}"
echo "=============================="

echo "Current Google Cloud project: gaurdia-ai"
echo "Current bucket: guardia_ai_vi"
echo -ne "${YELLOW}Use existing Google Cloud setup? (Y/n)${NC}: "
read use_existing_gcp

if [ "$use_existing_gcp" = "n" ] || [ "$use_existing_gcp" = "N" ]; then
    prompt_with_default "Google Cloud Project ID" "gaurdia-ai" GCP_PROJECT
    prompt_with_default "GCS Bucket Name" "guardia_ai_vi" GCS_BUCKET
    prompt_with_default "Credentials file path" "./guardia/config/google-credentials.json" GCP_CREDS
else
    GCP_PROJECT="gaurdia-ai"
    GCS_BUCKET="guardia_ai_vi"
    GCP_CREDS="./guardia/config/google-credentials.json"
    echo -e "${GREEN}Using existing Google Cloud setup${NC}"
fi

echo
echo -e "${BLUE}📧 Notification Settings${NC}"
echo "======================="

echo -ne "${YELLOW}Enable email notifications? (y/N)${NC}: "
read enable_email

if [ "$enable_email" = "y" ] || [ "$enable_email" = "Y" ]; then
    ENABLE_EMAIL="true"
    prompt_with_default "SMTP Host" "smtp.gmail.com" SMTP_HOST
    prompt_with_default "SMTP Port" "587" SMTP_PORT
    prompt_with_default "SMTP Username" "" SMTP_USER
    prompt_secret "SMTP Password" SMTP_PASS
    prompt_with_default "From Email" "$SMTP_USER" SMTP_FROM
else
    ENABLE_EMAIL="false"
    SMTP_HOST="smtp.gmail.com"
    SMTP_PORT="587"
    SMTP_USER=""
    SMTP_PASS=""
    SMTP_FROM=""
fi

echo -ne "${YELLOW}Enable SMS notifications (Twilio)? (y/N)${NC}: "
read enable_sms

if [ "$enable_sms" = "y" ] || [ "$enable_sms" = "Y" ]; then
    ENABLE_SMS="true"
    prompt_with_default "Twilio Account SID" "" TWILIO_SID
    prompt_secret "Twilio Auth Token" TWILIO_TOKEN
    prompt_with_default "Twilio From Number" "+1234567890" TWILIO_FROM
else
    ENABLE_SMS="false"
    TWILIO_SID=""
    TWILIO_TOKEN=""
    TWILIO_FROM=""
fi

echo
echo -e "${BLUE}📹 Camera Configuration${NC}"
echo "======================"

prompt_with_default "Camera sources (comma-separated)" "0" CAMERA_SOURCES
prompt_with_default "Face detection confidence (0.0-1.0)" "0.5" FACE_CONFIDENCE
prompt_with_default "Object detection confidence (0.0-1.0)" "0.5" OBJECT_CONFIDENCE

echo
echo -e "${BLUE}📝 Writing configuration...${NC}"

# Create the .env file
cat > .env << EOF
# Guardia AI Enhanced System - Complete Environment Configuration
# Generated on $(date)

# =============================================================================
# CORE APPLICATION SETTINGS
# =============================================================================
ENVIRONMENT=$ENVIRONMENT
SECRET_KEY=$SECRET_KEY
DEBUG=$DEBUG
HOST=$HOST
PORT=$PORT

# =============================================================================
# DATABASE CONFIGURATION - MongoDB Atlas
# =============================================================================
MONGODB_URL=$MONGODB_URL
MONGODB_DATABASE=$MONGODB_DATABASE

# =============================================================================
# GOOGLE CLOUD CONFIGURATION
# =============================================================================
GOOGLE_APPLICATION_CREDENTIALS=$GCP_CREDS
GCS_BUCKET_NAME=$GCS_BUCKET
GOOGLE_CLOUD_PROJECT_ID=$GCP_PROJECT
ENABLE_VIDEO_INTELLIGENCE=true
VIDEO_INTELLIGENCE_FEATURES=PERSON_DETECTION,OBJECT_TRACKING,FACE_DETECTION

# =============================================================================
# CAMERA AND DETECTION SETTINGS
# =============================================================================
CAMERA_SOURCES=$CAMERA_SOURCES
FACE_DETECTION_CONFIDENCE=$FACE_CONFIDENCE
OBJECT_DETECTION_CONFIDENCE=$OBJECT_CONFIDENCE
MASK_DETECTION_CONFIDENCE=0.5
FRAME_SKIP_COUNT=2
MAX_FRAMES_BUFFER=30
ALERT_COOLDOWN_SECONDS=30
MAX_VIDEO_DURATION_SECONDS=30

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================
MEDIA_STORAGE_PATH=./storage/media
IMAGES_PATH=./storage/images
VIDEOS_PATH=./storage/videos
FACES_PATH=./storage/faces
LOGS_PATH=./storage/logs
MAX_STORAGE_SIZE_MB=5000

# =============================================================================
# SECURITY AND AUTHENTICATION
# =============================================================================
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:8000","http://localhost:8080"]
CORS_CREDENTIALS=true
JWT_EXPIRATION_MINUTES=$JWT_EXPIRATION
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
SESSION_TIMEOUT_MINUTES=30

# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================

# Email Notifications
ENABLE_EMAIL_NOTIFICATIONS=$ENABLE_EMAIL
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SMTP_USERNAME=$SMTP_USER
SMTP_PASSWORD=$SMTP_PASS
SMTP_FROM_EMAIL=$SMTP_FROM

# SMS Notifications
ENABLE_SMS_NOTIFICATIONS=$ENABLE_SMS
TWILIO_ACCOUNT_SID=$TWILIO_SID
TWILIO_AUTH_TOKEN=$TWILIO_TOKEN
TWILIO_FROM_NUMBER=$TWILIO_FROM

# Push Notifications
ENABLE_PUSH_NOTIFICATIONS=true

# =============================================================================
# AI/ML MODEL SETTINGS
# =============================================================================
FACE_DETECTION_BACKEND=mediapipe
YOLO_MODEL_SIZE=yolov8n.pt
YOLO_DEVICE=cpu
AUTO_UPDATE_MODELS=false
MODEL_UPDATE_INTERVAL_HOURS=24

# =============================================================================
# ADVANCED FEATURES
# =============================================================================
ENABLE_BEHAVIOR_ANALYSIS=true
LOITERING_THRESHOLD_SECONDS=30
CROWD_DETECTION_THRESHOLD=5
ENABLE_NIGHT_MODE=true
NIGHT_MODE_START_HOUR=22
NIGHT_MODE_END_HOUR=6
BLUR_FACES_IN_RECORDINGS=false
ANONYMIZE_UNKNOWN_PERSONS=false

# =============================================================================
# LOGGING AND MONITORING
# =============================================================================
LOG_LEVEL=INFO
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
ENABLE_PERFORMANCE_MONITORING=true
PERFORMANCE_SAMPLING_RATE=0.1

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================
ENABLE_API_DOCS=true
ENABLE_RELOAD=true
ENABLE_PROFILING=false
TEST_MODE=false
MOCK_CAMERAS=false

# =============================================================================
# CLEANUP AND MAINTENANCE
# =============================================================================
ENABLE_AUTO_CLEANUP=true
CLEANUP_INTERVAL_HOURS=24
RETAIN_MEDIA_DAYS=30
RETAIN_LOGS_DAYS=7
ENABLE_AUTO_BACKUP=false
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30

# =============================================================================
# REDIS CACHE CONFIGURATION
# =============================================================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
EOF

echo -e "${GREEN}✅ Configuration written to .env${NC}"

# Create storage directories
echo -e "${BLUE}📁 Creating storage directories...${NC}"
mkdir -p storage/{media,images,videos,faces,logs}
echo -e "${GREEN}✅ Storage directories created${NC}"

# Validate configuration
echo -e "${BLUE}🔍 Validating configuration...${NC}"
if python validate_config.py; then
    echo
    echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
    echo
    echo "Next steps:"
    echo "1. Install dependencies: pip install -r requirements.txt"
    echo "2. Start the system: python start_server.py"
    echo "3. Access API docs: http://localhost:$PORT/docs"
    echo
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${YELLOW}⚠️  Production environment detected!${NC}"
        echo "Additional recommendations:"
        echo "• Use HTTPS with SSL certificates"
        echo "• Configure firewall rules"
        echo "• Set up monitoring and alerting"
        echo "• Regular security updates"
    fi
else
    echo -e "${RED}❌ Configuration validation failed${NC}"
    echo "Please check the errors above and run the setup again."
    exit 1
fi
