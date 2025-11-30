# Alerting Service

Real-time event notification delivery via WebSocket and webhooks.

## Features

- **WebSocket Server** - Real-time bidirectional communication
- **Webhook Support** - HTTP POST notifications to external systems
- **Severity Filtering** - Configurable minimum alert threshold
- **Connection Management** - Multiple concurrent WebSocket clients
- **Recent Alerts Cache** - Last 100 alerts in Redis

## WebSocket Protocol

Connect to: `ws://host:8007/ws/alerts`

### Message Format

```json
{
  "type": "alert",
  "event": {
    "event_id": "evt_cam_01_20231129120000",
    "event_class": "fight",
    "severity": "critical",
    "confidence": 0.92,
    ...
  },
  "timestamp": "2023-11-29T12:00:00.123456",
  "severity": "critical",
  "camera_id": "cam_01"
}
```

### Client Messages

- `ping` → Server responds with `{"type": "pong"}`

## Webhook Configuration

Set `WEBHOOK_ENABLED=true` and `WEBHOOK_URL=https://your-endpoint.com/alerts`

Webhook payload = event JSON with additional metadata.

## Configuration

- `FUSION_CONTROLLER_HOST`: FusionController hostname
- `FUSION_CONTROLLER_ZMQ_PORT`: Event subscription port (default: 5560)
- `REDIS_URL`: Redis connection URL
- `WEBHOOK_ENABLED`: Enable webhook notifications (default: false)
- `WEBHOOK_URL`: Webhook endpoint URL
- `MIN_ALERT_SEVERITY`: Minimum severity to alert (low/medium/high/critical)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Service status
- `GET /alerts/recent` - Get last 20 alerts
- `WS /ws/alerts` - WebSocket connection
