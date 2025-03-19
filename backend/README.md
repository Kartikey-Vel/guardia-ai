# Guardia AI Backend

The backend server for Guardia AI security and surveillance system. This FastAPI application provides the API endpoints, real-time notifications, and AI processing capabilities for the Guardia AI platform.

## Features

- **Authentication API**: JWT-based authentication system
- **Events API**: Security event logging and retrieval
- **Notifications**: WebSocket-based real-time alert system
- **AI Processing**: Video and audio analysis for security threats

## Setup & Installation

### Prerequisites

- Python 3.10+
- MongoDB 4.4+

### Environment Setup

1. Clone the repository
2. Navigate to the backend directory
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and configure your environment variables:
   ```bash
   cp .env.example .env
   # Edit the .env file with your settings
   ```

### Running the Server

For development:

```bash
python -m src.main
```

For production (using Uvicorn):

```bash
uvicorn src.api.sylvester_main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

Run tests using pytest:

```bash
pytest -v
```

## Docker Deployment

Build and run using Docker:

```bash
docker build -t guardia-backend .
docker run -p 8000:8000 --env-file .env guardia-backend
```

Or use Docker Compose to run the full stack:

```bash
docker-compose up -d
```
