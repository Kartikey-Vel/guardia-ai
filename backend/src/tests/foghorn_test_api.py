import pytest
import httpx
import json
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timedelta
from src.api.sylvester_main import app
from src.api.tweety_auth import create_access_token
from src.db.porky_mongo import get_users_collection, get_events_collection
from src.config.yosemite_config import settings

# Test client
client = TestClient(app)

# Test data
test_user = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "test_password",
    "full_name": "Test User"
}

test_event = {
    "event_type": "motion_detected", 
    "description": "Motion detected in restricted area",
    "threat_level": {"level": "medium", "score": 0.75},
    "location": "Building A, Zone 2",
    "video_clip_url": "https://storage.example.com/clips/abc123.mp4"
}

@pytest.fixture
async def setup_test_data():
    """Setup test data in the database."""
    # Get collections
    users_collection = await get_users_collection()
    events_collection = await get_events_collection()
    
    # Clear previous test data
    await users_collection.delete_many({"username": test_user["username"]})
    await events_collection.delete_many({"description": {"$regex": "test"}})
    
    # Create test user
    from src.api.tweety_auth import get_password_hash
    hashed_password = get_password_hash(test_user["password"])
    await users_collection.insert_one({
        "username": test_user["username"],
        "email": test_user["email"],
        "hashed_password": hashed_password,
        "full_name": test_user["full_name"],
        "disabled": False
    })
    
    yield
    
    # Cleanup after tests
    await users_collection.delete_many({"username": test_user["username"]})
    await events_collection.delete_many({"description": {"$regex": "test"}})

@pytest.fixture
def auth_token():
    """Create a test authentication token."""
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": test_user["username"]}, expires_delta=access_token_expires
    )
    return access_token

def test_health_endpoint():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"

def test_auth_endpoints(setup_test_data):
    """Test the authentication endpoints."""
    # Test login
    response = client.post(
        "/auth/token",
        data={"username": test_user["username"], "password": test_user["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Test failed login
    response = client.post(
        "/auth/token",
        data={"username": test_user["username"], "password": "wrong_password"},
    )
    assert response.status_code == 401

def test_events_endpoints(setup_test_data, auth_token):
    """Test the events endpoints."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test event creation
    response = client.post(
        "/events/",
        headers=headers,
        json=test_event
    )
    assert response.status_code == 201
    data = response.json()
    event_id = data["event_id"]
    assert data["event_type"] == test_event["event_type"]
    assert data["threat_level"]["level"] == test_event["threat_level"]["level"]
    
    # Test events retrieval
    response = client.get("/events/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test event acknowledgment
    response = client.put(f"/events/{event_id}/acknowledge", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] == True
    assert data["acknowledged_by"] == test_user["username"]

@pytest.mark.asyncio
async def test_websocket(setup_test_data, auth_token):
    """Test the WebSocket connection."""
    import websockets
    import json
    
    # Start a WebSocket client
    uri = f"ws://localhost:8000/notify/ws/testclient"
    
    async with websockets.connect(uri) as websocket:
        # Send a test message
        test_message = json.dumps({"type": "ping", "message": "Hello WebSocket"})
        await websocket.send(test_message)
        
        # Receive the acknowledgment
        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "ack"
        assert "timestamp" in response_data
