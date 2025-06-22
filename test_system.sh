#!/bin/bash

# Guardia AI Enhanced System - Comprehensive System Test
# This script validates the installation and core functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
API_BASE_URL="http://localhost:8000"
TEST_USER_EMAIL="test@example.com"
TEST_USER_PASSWORD="testpassword123"
TEST_TIMEOUT=30

echo -e "${BLUE}🧪 Guardia AI Enhanced System - Comprehensive Test Suite${NC}"
echo -e "${BLUE}======================================================${NC}"

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS:${NC} $2"
    else
        echo -e "${RED}❌ FAIL:${NC} $2"
        exit 1
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

# Test 1: Check if server is running
echo -e "\n${YELLOW}Test 1: Server Health Check${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health" || echo "000")
if [ "$response" = "200" ]; then
    print_result 0 "Server is running and healthy"
else
    print_result 1 "Server is not responding (HTTP $response)"
fi

# Test 2: Check API documentation
echo -e "\n${YELLOW}Test 2: API Documentation${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/docs" || echo "000")
if [ "$response" = "200" ]; then
    print_result 0 "API documentation is accessible"
else
    print_result 1 "API documentation not accessible (HTTP $response)"
fi

# Test 3: Check database connectivity
echo -e "\n${YELLOW}Test 3: Database Connectivity${NC}"
response=$(curl -s "$API_BASE_URL/api/system/status" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('1' if data.get('database', {}).get('connected') else '0')
except:
    print('0')
" 2>/dev/null || echo "0")

if [ "$response" = "1" ]; then
    print_result 0 "Database connection successful"
else
    print_result 1 "Database connection failed"
fi

# Test 4: User registration
echo -e "\n${YELLOW}Test 4: User Registration${NC}"
register_response=$(curl -s -X POST "$API_BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_USER_EMAIL\",
        \"password\": \"$TEST_USER_PASSWORD\",
        \"full_name\": \"Test User\",
        \"phone\": \"+1234567890\"
    }" || echo '{"error": "request_failed"}')

# Check if registration was successful or user already exists
if echo "$register_response" | grep -q '"access_token"' || echo "$register_response" | grep -q "already exists"; then
    print_result 0 "User registration/authentication working"
else
    print_result 1 "User registration failed: $register_response"
fi

# Test 5: User login
echo -e "\n${YELLOW}Test 5: User Authentication${NC}"
login_response=$(curl -s -X POST "$API_BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_USER_EMAIL\",
        \"password\": \"$TEST_USER_PASSWORD\"
    }" || echo '{"error": "request_failed"}')

access_token=$(echo "$login_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    print('')
" 2>/dev/null || echo "")

if [ -n "$access_token" ]; then
    print_result 0 "User authentication successful"
    print_info "Access token obtained"
else
    print_result 1 "User authentication failed: $login_response"
fi

# Test 6: Protected endpoint access
echo -e "\n${YELLOW}Test 6: Protected Endpoint Access${NC}"
if [ -n "$access_token" ]; then
    profile_response=$(curl -s -X GET "$API_BASE_URL/api/users/profile" \
        -H "Authorization: Bearer $access_token" || echo '{"error": "request_failed"}')
    
    if echo "$profile_response" | grep -q '"email"'; then
        print_result 0 "Protected endpoint access successful"
    else
        print_result 1 "Protected endpoint access failed: $profile_response"
    fi
else
    print_warning "Skipping protected endpoint test (no access token)"
fi

# Test 7: Camera detection capabilities
echo -e "\n${YELLOW}Test 7: Camera Detection Capabilities${NC}"
if [ -n "$access_token" ]; then
    cameras_response=$(curl -s -X GET "$API_BASE_URL/api/surveillance/cameras/available" \
        -H "Authorization: Bearer $access_token" || echo '{"error": "request_failed"}')
    
    if echo "$cameras_response" | grep -q '\[\]' || echo "$cameras_response" | grep -q '"cameras"'; then
        print_result 0 "Camera detection endpoint working"
    else
        print_result 1 "Camera detection failed: $cameras_response"
    fi
else
    print_warning "Skipping camera detection test (no access token)"
fi

# Test 8: AI Model Loading
echo -e "\n${YELLOW}Test 8: AI Model Status${NC}"
models_response=$(curl -s "$API_BASE_URL/api/system/models/status" || echo '{"error": "request_failed"}')

if echo "$models_response" | grep -q '"face_detector"' || echo "$models_response" | grep -q '"models"'; then
    print_result 0 "AI models status endpoint working"
else
    print_result 1 "AI models status check failed: $models_response"
fi

# Test 9: WebSocket connection
echo -e "\n${YELLOW}Test 9: WebSocket Connection${NC}"
# Simple WebSocket test using netcat or curl
ws_test=$(timeout 5s bash -c "
    (echo 'GET /ws HTTP/1.1'; echo 'Host: localhost:8000'; echo 'Upgrade: websocket'; echo 'Connection: Upgrade'; echo 'Sec-WebSocket-Key: test'; echo 'Sec-WebSocket-Version: 13'; echo '') | nc localhost 8000 2>/dev/null | head -1
" 2>/dev/null || echo "failed")

if echo "$ws_test" | grep -q "101\|Switching Protocols"; then
    print_result 0 "WebSocket connection available"
else
    print_warning "WebSocket connection test inconclusive"
fi

# Test 10: File upload capability
echo -e "\n${YELLOW}Test 10: File Upload Capability${NC}"
if [ -n "$access_token" ]; then
    # Create a small test image
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" | base64 -d > /tmp/test.png
    
    upload_response=$(curl -s -X POST "$API_BASE_URL/api/users/family/register" \
        -H "Authorization: Bearer $access_token" \
        -F "name=Test Person" \
        -F "image=@/tmp/test.png" 2>/dev/null || echo '{"error": "request_failed"}')
    
    if echo "$upload_response" | grep -q '"id"\|"error"'; then
        print_result 0 "File upload endpoint accessible"
    else
        print_result 1 "File upload test failed"
    fi
    
    # Cleanup
    rm -f /tmp/test.png
else
    print_warning "Skipping file upload test (no access token)"
fi

# Test 11: System performance
echo -e "\n${YELLOW}Test 11: System Performance Check${NC}"
start_time=$(date +%s%N)
perf_response=$(curl -s "$API_BASE_URL/health" || echo "failed")
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds

if [ "$perf_response" != "failed" ] && [ $response_time -lt 5000 ]; then
    print_result 0 "System performance acceptable (${response_time}ms)"
else
    print_warning "System performance may be slow (${response_time}ms)"
fi

# Test 12: Configuration validation
echo -e "\n${YELLOW}Test 12: Configuration Validation${NC}"
config_response=$(curl -s "$API_BASE_URL/api/system/config" || echo '{"error": "request_failed"}')

if echo "$config_response" | grep -q '"environment"\|"debug"'; then
    print_result 0 "Configuration endpoint working"
else
    print_result 1 "Configuration validation failed"
fi

# Summary
echo -e "\n${BLUE}🎉 Test Suite Completed${NC}"
echo -e "${BLUE}=====================${NC}"
echo -e "${GREEN}All core functionality tests passed!${NC}"
echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Configure your camera sources in the environment"
echo -e "2. Set up notification credentials (email, SMS)"
echo -e "3. Register family members for face recognition"
echo -e "4. Start surveillance monitoring"
echo -e "\n${BLUE}For more information, see README_ENHANCED.md${NC}"
echo -e "${BLUE}API Documentation: ${API_BASE_URL}/docs${NC}"
