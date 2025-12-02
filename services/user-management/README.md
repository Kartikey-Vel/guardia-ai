# User Management Service

Comprehensive user profile and family member management for Guardia AI with biometric data support.

## Overview

The User Management Service provides:

- **User Profile Management**: Complete user accounts with preferences
- **Family Member Registry**: Add and manage protected family members
- **Biometric Data Storage**: Secure face encoding storage for recognition
- **Access Control**: Role-based permissions and API key management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Management Service                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Profile   │  │   Family    │  │    Biometric Store      │ │
│  │   Manager   │  │   Registry  │  │   (Face Encodings)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │               │                      │                 │
│         └───────────────┼──────────────────────┘                │
│                         │                                        │
│                   ┌─────▼─────┐                                 │
│                   │  SQLite   │                                 │
│                   │  Database │                                 │
│                   └───────────┘                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         │                                         │
         ▼                                         ▼
   Cloud API (HTTP)                    Security Fusion (Face Data)
```

## API Endpoints

### User Profiles

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profile` | GET | Get current user profile |
| `/profile` | POST | Create new user profile |
| `/profile` | PUT | Update user profile |
| `/profile/preferences` | PUT | Update notification preferences |

### Family Members

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/family` | GET | List all family members |
| `/family` | POST | Add new family member |
| `/family/{member_id}` | GET | Get specific family member |
| `/family/{member_id}` | PUT | Update family member |
| `/family/{member_id}` | DELETE | Remove family member |
| `/family/{member_id}/face` | POST | Upload face image for recognition |
| `/family/{member_id}/face` | DELETE | Remove face encoding |

### Biometric Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/biometrics/faces` | GET | Get all face encodings (for Security Fusion) |
| `/biometrics/verify` | POST | Verify face against stored encodings |
| `/biometrics/stats` | GET | Get biometric data statistics |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/metrics` | GET | Prometheus metrics |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_MANAGEMENT_PORT` | `8012` | Service port |
| `DATABASE_URL` | `sqlite:///users.db` | SQLite database path |
| `MAX_FAMILY_MEMBERS` | `10` | Max family members per user |
| `FACE_ENCODING_DIM` | `128` | Face encoding vector dimension |
| `FACE_MATCH_THRESHOLD` | `0.6` | Face matching confidence threshold |
| `LOG_LEVEL` | `INFO` | Logging level |

## Data Models

### User Profile

```python
{
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-01T00:00:00Z",
    "preferences": {
        "notifications_enabled": true,
        "alert_sounds": true,
        "email_alerts": true,
        "push_notifications": true,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00"
    },
    "role": "owner",
    "active": true
}
```

### Family Member

```python
{
    "id": "uuid",
    "name": "Jane Doe",
    "relationship": "spouse",
    "role": "protected",  # owner, protected, guest
    "phone": "+1234567890",
    "email": "jane@example.com",
    "has_face_encoding": true,
    "trusted": true,
    "created_at": "2024-01-01T00:00:00Z"
}
```

### Biometric Data

```python
{
    "member_id": "uuid",
    "encoding_type": "face",
    "encoding": [0.1, 0.2, ...],  # 128-dim vector
    "quality_score": 0.95,
    "created_at": "2024-01-01T00:00:00Z"
}
```

## Usage Examples

### Create User Profile

```bash
curl -X POST http://localhost:8012/profile \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "secure_password"
  }'
```

### Add Family Member

```bash
curl -X POST http://localhost:8012/family \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "relationship": "spouse",
    "role": "protected",
    "trusted": true
  }'
```

### Upload Face Image

```bash
curl -X POST http://localhost:8012/family/{member_id}/face \
  -F "image=@face_photo.jpg"
```

### Get All Face Encodings (for Security Fusion)

```bash
curl http://localhost:8012/biometrics/faces
```

## Integration with Security Fusion

The User Management Service provides face encodings to the Security Fusion service for real-time recognition:

1. **Face Registration**: When a family member's face is uploaded, it's encoded using face_recognition library
2. **Encoding Storage**: Face encodings (128-dim vectors) are stored in SQLite
3. **Data Access**: Security Fusion fetches encodings via `/biometrics/faces`
4. **Real-time Matching**: Security Fusion matches detected faces against stored encodings

## Security Considerations

1. **Face Data Encryption**: Face encodings are stored encrypted at rest
2. **Access Control**: API endpoints require authentication
3. **Rate Limiting**: Face upload endpoints are rate-limited
4. **Audit Logging**: All biometric operations are logged
5. **Data Retention**: Face data can be purged on user request

## Development

### Local Setup

```bash
cd services/user-management
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python src/main.py
```

### Testing

```bash
pytest tests/ -v
```

### Docker Build

```bash
docker build -t guardia/user-management:latest .
```

## Performance

| Operation | Typical Latency |
|-----------|----------------|
| Profile CRUD | < 10ms |
| Family Member CRUD | < 10ms |
| Face Encoding Generation | 200-500ms |
| Face Matching | < 50ms |
| Bulk Encoding Fetch | < 100ms |

## Dependencies

- `fastapi[all]`: Web framework
- `sqlalchemy`: Database ORM
- `face_recognition`: Face encoding generation
- `numpy`: Numerical operations
- `pydantic`: Data validation
- `python-jose`: JWT handling
- `bcrypt`: Password hashing

## Related Services

- **Security Fusion**: Consumes face encodings for recognition
- **Cloud API**: Proxies user management endpoints
- **Web Dashboard**: User and family management UI
