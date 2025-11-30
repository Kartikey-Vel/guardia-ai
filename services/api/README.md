# Guardia AI Cloud API Service

FastAPI-based cloud backend for event synchronization, model registry, analytics, and authentication.

## Features

- **Event Management**: Sync and query security events from edge devices
- **Model Registry**: Track AI model versions and metadata
- **Analytics**: Aggregated statistics and reporting
- **Authentication**: JWT-based auth with role-based access control (RBAC)
- **PostgreSQL**: TimescaleDB for time-series data
- **Prometheus**: Metrics for monitoring
- **OpenAPI**: Auto-generated documentation at `/docs`

---

## API Endpoints

### Health & Metrics

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Events

- `POST /events` - Create/sync event from edge
- `GET /events` - List events with filtering
- `GET /events/{event_id}` - Get event by ID
- `PATCH /events/{event_id}/acknowledge` - Acknowledge event
- `DELETE /events/{event_id}` - Delete event (admin only)

### Models

- `POST /models` - Register model version (admin only)
- `GET /models` - List models
- `GET /models/{model_id}` - Get model by ID

### Analytics

- `POST /analytics` - Get analytics data

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/guardia

# JWT
JWT_SECRET=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS
CORS_ORIGINS=http://localhost:3000,https://app.example.com

# Logging
LOG_LEVEL=INFO
SQL_ECHO=false
```

---

## Authentication

All endpoints except `/health`, `/auth/register`, and `/auth/login` require JWT authentication.

### Login Flow

1. **Register** (one-time):
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","username":"admin","password":"secure_password","role":"admin"}'
   ```

2. **Login**:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -d "username=admin&password=secure_password"
   ```
   
   Response:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer"
   }
   ```

3. **Use token** in subsequent requests:
   ```bash
   curl http://localhost:8000/events \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

---

## Example Usage

### Sync Event from Edge

```python
import httpx

event_data = {
    "event_id": "evt_20231129_001",
    "camera_id": "cam_front",
    "event_class": "fight_detected",
    "severity": "critical",
    "confidence": 0.92,
    "timestamp": "2023-11-29T10:30:00Z",
    "clip_url": "http://minio:9000/clips/evt_20231129_001.mp4",
    "metadata": {
        "model_contributions": {
            "skelegnn": 0.95,
            "motionstream": 0.88
        }
    }
}

response = httpx.post(
    "http://api:8000/events",
    json=event_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

### Query Events

```python
# Filter by severity and date range
params = {
    "severity": "critical",
    "start_date": "2023-11-29T00:00:00Z",
    "end_date": "2023-11-29T23:59:59Z",
    "limit": 20
}

response = httpx.get(
    "http://api:8000/events",
    params=params,
    headers={"Authorization": f"Bearer {token}"}
)

events = response.json()["events"]
```

### Get Analytics

```python
analytics_query = {
    "start_date": "2023-11-22T00:00:00Z",
    "end_date": "2023-11-29T23:59:59Z"
}

response = httpx.post(
    "http://api:8000/analytics",
    json=analytics_query,
    headers={"Authorization": f"Bearer {token}"}
)

analytics = response.json()
print(f"Total events: {analytics['total_events']}")
print(f"By severity: {analytics['events_by_severity']}")
```

---

## Database Schema

### Events Table

```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    event_class VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    frame_id VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    clip_url VARCHAR(500),
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_camera ON events(camera_id);
CREATE INDEX idx_events_severity ON events(severity);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_acknowledged ON events(acknowledged);
```

### Models Table

```sql
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    framework VARCHAR(50),
    input_shape JSONB,
    output_classes JSONB,
    weights_url VARCHAR(500),
    config JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'operator',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations (future)
alembic upgrade head

# Run locally
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Access docs
open http://localhost:8000/docs
```

---

## Production Deployment

1. **Set secure environment variables** (especially `JWT_SECRET`)
2. **Use PostgreSQL with SSL** in production
3. **Enable HTTPS** via reverse proxy (nginx/Traefik)
4. **Set up database backups** (pg_dump or continuous archiving)
5. **Monitor metrics** via Prometheus/Grafana

---

## Roles

- **operator**: Can view events, acknowledge events, view analytics
- **admin**: All operator permissions + user management, model registry, event deletion
