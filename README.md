# 🛡️ Guardia AI

Guardia AI is an advanced AI-powered security and surveillance assistant designed to detect, analyze, and respond to potential security threats in real time. Think of it as a **digital "Chaukidar"** that continuously monitors video and audio feeds to enhance safety and security across various environments.

---

## 🚀 Features

### 🎥 Video Processing (Computer Vision)
- **Motion Detection** – Identifies unusual movement in restricted areas.
- **Anomaly Detection** – Detects suspicious activities like fights, intrusions, and unattended objects.
- **Weapon & Fire Detection** – Recognizes guns, knives, and fire in real time.
- **Face Recognition (Optional)** – Identifies known individuals and potential threats.

### 🔊 Audio Processing (Sound Recognition)
- **Gunshot Detection** – Recognizes gunfire sounds instantly.
- **Scream Detection** – Detects distress calls and loud, unusual noises.
- **Alarm Sound Detection** – Identifies emergency sirens, fire alarms, and security alarms.

### ⚡ Smart Alert System
- **Threat Prioritization** – Categorizes threats as **low, medium, or high priority**.
- **Automated Notifications** – Alerts the right department based on the severity of the threat.
- **Incident Escalation** – If no response is received within a set timeframe, the alert is escalated to the next responsible authority.

---

## 🏗️ Tech Stack

| Component        | Technology |
|-----------------|------------|
| Frontend        | **Next.js** (React framework) |
| Backend        | **Node.js** (Express.js) |
| AI (Video)      | **OpenCV, TensorFlow, ONNX** |
| AI (Audio)      | **DeepSpeech, OpenAI Whisper, Librosa** |
| Database       | **MongoDB / PostgreSQL** |
| Real-Time Communication | **WebSockets** |
| Cloud Storage   | **AWS S3 / Firebase** |
| DevOps         | **Docker, Kubernetes** |

---

## 🐳 Docker Setup & Deployment

This project provides a production-ready Docker setup with two deployment options:

### Prerequisites
- Docker and Docker Compose installed
- Camera connected to the system (optional for testing)
- X11 server running (for GUI display on Linux)

### Quick Start

**Option 1: Using the run script (Recommended)**
```bash
chmod +x run.sh
./run.sh full        # Full AI surveillance
./run.sh minimal     # Minimal motion detection
./run.sh stop        # Stop containers
./run.sh logs        # View logs
./run.sh status      # Check status
```

**Option 2: Using docker-compose directly**
```bash
# Full AI surveillance
docker-compose up --build guardia-ai

# Minimal motion detection
docker-compose --profile minimal up --build guardia-ai-minimal
```

### Configuration

#### Environment Variables
The following environment variables are set by default:
- `DISPLAY=:0` (for GUI/X11 support)
- `PYTHONPATH=/app/src`
- `DEBIAN_FRONTEND=noninteractive`

#### Data Persistence
The following directories are automatically mounted for data persistence:
- `./data` → `/app/data` - Database and configuration files
- `./images` → `/app/images` - Store owner and family member images
- `./encodings` → `/app/encodings` - Face encodings are saved here
- `./faces` → `/app/faces` - Processed face images
- `./detected` → `/app/detected` - Detection results (known/unknown)
- `./logs` → `/app/logs` - Application logs
- `./config` → `/app/config` - Configuration files

#### Port Configuration
- Port `8000` is exposed for future web interface/API access
- Access at [http://localhost:8000](http://localhost:8000) (when implemented)

### Docker Images

#### Main Image (Dockerfile)
- **Base:** Python 3.11-slim with comprehensive AI dependencies
- **Features:** Full OpenCV, dlib, face_recognition, TensorFlow support
- **Includes:** Face recognition, weapon detection, advanced anomaly detection
- **Dependencies:** cmake, dlib, face-recognition, comprehensive OpenCV libraries
- **Security:** Runs as root (required for some AI libraries)
- **Size:** Larger but feature-complete (~2-3GB)
- **Use case:** Production environments with full AI capabilities

#### Minimal Image (Dockerfile.minimal)
- **Base:** Python 3.11-slim with essential dependencies only
- **Features:** Motion detection, basic OpenCV support
- **Includes:** Basic surveillance without face recognition
- **Dependencies:** Essential OpenCV libraries only
- **Security:** Lightweight footprint
- **Size:** Smaller (~500MB-1GB)
- **Use case:** Resource-constrained environments, testing, basic monitoring

### Usage Instructions

1. **Setup your images:**
   ```bash
   mkdir -p images
   # Place your owner and family member images in ./images/
   ```

2. **Start the surveillance system:**
   ```bash
   ./run.sh full
   ```

3. **Monitor logs:**
   ```bash
   ./run.sh logs
   ```

4. **Check status:**
   ```bash
   ./run.sh status
   ```

5. **Stop the system:**
   ```bash
   ./run.sh stop
   ```

### Troubleshooting

- **Camera issues:** Check device permissions and ensure camera is not in use by another application
- **GUI display problems:** 
  - Linux: Ensure X11 forwarding is enabled (`xhost +local:docker`)
  - Windows: Use WSL2 with Docker Desktop or VcXsrv
- **Performance issues:** Consider using the minimal profile for lower resource usage
- **Build failures:** Check system resources and try building with `--no-cache` flag

### Health Monitoring
The containers include health checks that monitor:
- Python runtime status
- Application responsiveness
- System resource availability

Access health status via:
```bash
docker-compose ps
docker inspect guardia-surveillance --format='{{.State.Health.Status}}'
```

---

## 📜 Manual Installation (Non-Docker)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/guardia-ai.git
cd guardia-ai
```

### 2️⃣ Install Dependencies
```bash
# Install backend dependencies
cd backend
npm install

# Install frontend dependencies
cd ../frontend
npm install
```

### 3️⃣ Start the Application
```bash
# Start backend server
cd backend
npm start

# Start frontend app
cd ../frontend
npm run dev
```

### 4️⃣ (Optional) Run AI Processing
```bash
# Install AI dependencies
pip install -r requirements.txt

# Start AI processing
python ai_processor.py
```

---

## 🏢 Use Cases
- **Corporate Security** – Monitor office spaces for unauthorized access.
- **Educational Institutions** – Ensure student safety by detecting fights or threats.
- **Public Spaces** – Enhance security at malls, train stations, and airports.
- **Retail & Warehouses** – Detect theft or vandalism in real time.

---

## 🤝 Contributing
Want to contribute? Great! Here's how you can help:
- 🚀 Fork the repo & create a new feature branch.
- 🛠️ Submit a pull request with a detailed description.
- 💡 Suggest improvements or report issues in the GitHub Issues tab.

---

## 🔐 License
This project is licensed under the **MIT License**.

---

## 📬 Contact
For inquiries or collaboration opportunities, reach out to:
📧 **aryanbajpai2411@outlook.com**  
🌐 [LinkedIn](https://linkedin.com/in/codernotme)
