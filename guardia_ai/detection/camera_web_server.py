#!/usr/bin/env python3
"""
Camera Connection Web Server for Guardia AI
Simple Flask server to handle IP camera connections
"""

from flask import Flask, request, jsonify, render_template_string
import threading
import json
import os
from datetime import datetime

class CameraWebServer:
    """Simple web server for camera connection"""
    
    def __init__(self, camera_manager, port=8080):
        self.camera_manager = camera_manager
        self.port = port
        self.app = Flask(__name__)
        self.server_thread = None
        self.running = False
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Guardia AI - Camera Connection</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                    .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
                    .form-group { margin-bottom: 20px; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                    button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
                    button:hover { background: #2980b9; }
                    .status { margin-top: 20px; padding: 10px; border-radius: 5px; }
                    .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                    .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Guardia AI</h1>
                        <h2>Camera Connection Setup</h2>
                    </div>
                    
                    <form id="cameraForm">
                        <div class="form-group">
                            <label for="cameraName">Camera Name:</label>
                            <input type="text" id="cameraName" name="name" placeholder="Living Room Camera" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="cameraType">Camera Type:</label>
                            <select id="cameraType" name="type" onchange="toggleUrlField()">
                                <option value="ip">IP Camera (HTTP/MJPEG)</option>
                                <option value="rtsp">RTSP Stream</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label for="cameraUrl">Camera URL:</label>
                            <input type="url" id="cameraUrl" name="url" placeholder="http://192.168.1.100:8080/video" required>
                            <small>Examples:<br>
                            • IP Camera: http://192.168.1.100:8080/video<br>
                            • RTSP: rtsp://192.168.1.100:554/stream</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="description">Description (Optional):</label>
                            <input type="text" id="description" name="description" placeholder="Front door security camera">
                        </div>
                        
                        <button type="submit">Connect Camera</button>
                        <button type="button" onclick="testConnection()">Test Connection</button>
                    </form>
                    
                    <div id="status"></div>
                    
                    <div style="margin-top: 30px;">
                        <h3>Connected Cameras</h3>
                        <div id="cameraList"></div>
                        <button type="button" onclick="refreshCameraList()">Refresh List</button>
                    </div>
                </div>
                
                <script>
                function toggleUrlField() {
                    const type = document.getElementById('cameraType').value;
                    const urlField = document.getElementById('cameraUrl');
                    if (type === 'rtsp') {
                        urlField.placeholder = 'rtsp://192.168.1.100:554/stream';
                    } else {
                        urlField.placeholder = 'http://192.168.1.100:8080/video';
                    }
                }
                
                document.getElementById('cameraForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const data = Object.fromEntries(formData);
                    
                    fetch('/connect', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    })
                    .then(response => response.json())
                    .then(data => {
                        const status = document.getElementById('status');
                        if (data.success) {
                            status.innerHTML = '<div class="status success">Camera connected successfully!</div>';
                            refreshCameraList();
                        } else {
                            status.innerHTML = '<div class="status error">Error: ' + data.error + '</div>';
                        }
                    });
                });
                
                function testConnection() {
                    const url = document.getElementById('cameraUrl').value;
                    const type = document.getElementById('cameraType').value;
                    
                    fetch('/test', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url, type: type})
                    })
                    .then(response => response.json())
                    .then(data => {
                        const status = document.getElementById('status');
                        if (data.success) {
                            status.innerHTML = '<div class="status success">Connection test successful!</div>';
                        } else {
                            status.innerHTML = '<div class="status error">Connection test failed: ' + data.error + '</div>';
                        }
                    });
                }
                
                function refreshCameraList() {
                    fetch('/cameras')
                    .then(response => response.json())
                    .then(data => {
                        const list = document.getElementById('cameraList');
                        let html = '';
                        data.cameras.forEach(camera => {
                            const statusColor = camera.is_active ? 'green' : 'red';
                            html += `<div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                <strong>${camera.name}</strong> (${camera.type})<br>
                                <small>Status: <span style="color: ${statusColor}">${camera.status}</span></small><br>
                                <small>Path: ${camera.path}</small>
                            </div>`;
                        });
                        list.innerHTML = html || '<p>No cameras connected</p>';
                    });
                }
                
                // Load camera list on page load
                refreshCameraList();
                </script>
            </body>
            </html>
            ''')
        
        @self.app.route('/connect', methods=['POST'])
        def connect_camera():
            try:
                data = request.json
                name = data.get('name', 'IP Camera')
                camera_type = data.get('type', 'ip')
                url = data.get('url', '')
                description = data.get('description', '')
                
                if not url:
                    return jsonify({'success': False, 'error': 'URL is required'})
                
                # Add camera to manager
                source_id, success, message = self.camera_manager.add_camera(
                    camera_type, url, name, description
                )
                
                if success:
                    return jsonify({
                        'success': True, 
                        'message': message,
                        'camera_id': source_id
                    })
                else:
                    return jsonify({'success': False, 'error': message})
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/test', methods=['POST'])
        def test_camera():
            try:
                data = request.json
                url = data.get('url', '')
                
                if not url:
                    return jsonify({'success': False, 'error': 'URL is required'})
                
                success, message = self.camera_manager.test_ip_camera_url(url)
                return jsonify({'success': success, 'message': message})
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/cameras')
        def get_cameras():
            try:
                status = self.camera_manager.get_camera_status()
                return jsonify(status)
            except Exception as e:
                return jsonify({'error': str(e)})
        
        @self.app.route('/setup')
        def setup():
            """Setup page that can be accessed via QR code"""
            camera_name = request.args.get('name', 'New Camera')
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Guardia AI - Quick Setup</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; text-align: center; }
                    .container { max-width: 400px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    h1 { color: #2c3e50; }
                    .qr-info { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    button { background: #3498db; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🛡️ Guardia AI</h1>
                    <h2>Camera Setup Complete!</h2>
                    <div class="qr-info">
                        <p>Your camera "{{ camera_name }}" can now connect to the Guardia AI system.</p>
                        <p>Configure your camera to stream to this server.</p>
                    </div>
                    <button onclick="window.location.href='/'">Manage Cameras</button>
                </div>
            </body>
            </html>
            ''', camera_name=camera_name)
        
        @self.app.route('/wifi-setup')
        def wifi_setup():
            """CareCam-style Wi-Fi setup page"""
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Guardia AI - Wi-Fi Camera Setup</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                    .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
                    .form-group { margin-bottom: 20px; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                    button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                    button:hover { background: #2980b9; }
                    .qr-container { text-align: center; margin: 20px 0; }
                    .info { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    .step { background: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 4px solid #3498db; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Guardia AI</h1>
                        <h2>📱 Smart Camera Wi-Fi Setup</h2>
                        <p>Connect your smart camera to your Wi-Fi network</p>
                    </div>
                    
                    <div class="info">
                        <h3>📋 Setup Instructions</h3>
                        <div class="step">
                            <strong>Step 1:</strong> Enter your Wi-Fi network details below
                        </div>
                        <div class="step">
                            <strong>Step 2:</strong> Click "Generate QR Code" to create a configuration code
                        </div>
                        <div class="step">
                            <strong>Step 3:</strong> Scan the QR code with your smart camera
                        </div>
                        <div class="step">
                            <strong>Step 4:</strong> Your camera will connect to Wi-Fi and register with Guardia AI
                        </div>
                    </div>
                    
                    <form id="wifiForm">
                        <div class="form-group">
                            <label for="ssid">📶 Wi-Fi Network Name (SSID):</label>
                            <input type="text" id="ssid" name="ssid" placeholder="MyHomeNetwork" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="password">🔒 Wi-Fi Password:</label>
                            <input type="password" id="password" name="password" placeholder="Your Wi-Fi password" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="cameraName">📹 Camera Name:</label>
                            <input type="text" id="cameraName" name="camera_name" placeholder="Living Room Camera" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="encryption">🔐 Security Type:</label>
                            <select id="encryption" name="encryption">
                                <option value="WPA2">WPA2 (Most Common)</option>
                                <option value="WPA3">WPA3 (Latest)</option>
                                <option value="WPA">WPA (Legacy)</option>
                                <option value="WEP">WEP (Old/Insecure)</option>
                                <option value="OPEN">Open (No Security)</option>
                            </select>
                        </div>
                        
                        <button type="submit">📱 Generate QR Code</button>
                        <button type="button" onclick="clearForm()">🗑️ Clear Form</button>
                    </form>
                    
                    <div id="qrResult"></div>
                    <div id="status"></div>
                </div>
                
                <script>
                document.getElementById('wifiForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    generateWifiQR();
                });
                
                function generateWifiQR() {
                    const formData = new FormData(document.getElementById('wifiForm'));
                    const data = Object.fromEntries(formData);
                    
                    showStatus('Generating QR code...', 'info');
                    
                    fetch('/api/wifi-qr', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            displayQRCode(data.qr_data, data.guardia_url);
                            showStatus('QR code generated! Scan with your camera.', 'success');
                        } else {
                            showStatus('Error: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        showStatus('Network error: ' + error.message, 'error');
                    });
                }
                
                function displayQRCode(qrData, guardiaUrl) {
                    const qrResult = document.getElementById('qrResult');
                    qrResult.innerHTML = `
                        <div class="qr-container">
                            <h3>📱 Scan this QR code with your smart camera</h3>
                            <div style="background: white; padding: 20px; display: inline-block; border-radius: 10px;">
                                <img src="data:image/png;base64,${qrData}" alt="Wi-Fi Setup QR Code" style="max-width: 300px;">
                            </div>
                            <p><strong>Setup URL:</strong> <a href="${guardiaUrl}" target="_blank">${guardiaUrl}</a></p>
                            <p><em>After scanning, your camera should automatically connect to Wi-Fi and register with Guardia AI</em></p>
                        </div>
                    `;
                }
                
                function clearForm() {
                    document.getElementById('wifiForm').reset();
                    document.getElementById('qrResult').innerHTML = '';
                    document.getElementById('status').innerHTML = '';
                }
                
                function showStatus(message, type) {
                    const status = document.getElementById('status');
                    const className = type === 'success' ? 'success' : type === 'error' ? 'error' : 'info';
                    status.innerHTML = `<div class="status ${className}">${message}</div>`;
                }
                </script>
            </body>
            </html>
            ''')
        
        @self.app.route('/api/wifi-qr', methods=['POST'])
        def generate_wifi_qr():
            """Generate Wi-Fi configuration QR code for smart cameras"""
            try:
                data = request.get_json()
                ssid = data.get('ssid', '').strip()
                password = data.get('password', '').strip()
                camera_name = data.get('camera_name', '').strip()
                encryption = data.get('encryption', 'WPA2')
                
                if not ssid or not camera_name:
                    return jsonify({
                        'status': 'error',
                        'message': 'SSID and camera name are required'
                    })
                
                # Create Wi-Fi configuration string (Android/iOS standard format)
                wifi_config = f"WIFI:T:{encryption};S:{ssid};P:{password};H:false;;"
                
                # Add Guardia AI connection information
                guardia_host = self.camera_manager.get_local_ip()
                guardia_port = self.port
                guardia_url = f"http://{guardia_host}:{guardia_port}/camera-register"
                
                # Create comprehensive setup data for smart cameras
                setup_data = {
                    'wifi': wifi_config,
                    'guardia_url': guardia_url,
                    'camera_name': camera_name,
                    'setup_timestamp': datetime.now().isoformat(),
                    'version': '1.0'
                }
                
                # Generate QR code with setup data
                import qrcode
                import base64
                from io import BytesIO
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(json.dumps(setup_data))
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_str = base64.b64encode(buffer.getvalue()).decode()
                
                return jsonify({
                    'status': 'success',
                    'qr_data': img_str,
                    'setup_data': setup_data,
                    'guardia_url': guardia_url,
                    'wifi_config': wifi_config
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to generate QR code: {str(e)}'
                })
        
        @self.app.route('/camera-register', methods=['POST', 'GET'])
        def camera_register():
            """Endpoint for smart cameras to register after Wi-Fi setup"""
            if request.method == 'GET':
                # Provide registration form for manual setup
                return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Guardia AI - Camera Registration</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                        .container { max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>📹 Camera Registration</h2>
                        <p>Complete your smart camera setup:</p>
                        <form method="post">
                            <p><label>Camera Name: <input type="text" name="name" required></label></p>
                            <p><label>Stream URL: <input type="url" name="stream_url" required></label></p>
                            <p><label>Camera Type: 
                                <select name="camera_type">
                                    <option value="ip">IP Camera</option>
                                    <option value="rtsp">RTSP Stream</option>
                                </select>
                            </label></p>
                            <p><button type="submit">Register Camera</button></p>
                        </form>
                    </div>
                </body>
                </html>
                ''')
            
            try:
                # Handle POST registration from smart cameras
                if request.content_type == 'application/json':
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                name = data.get('name', '').strip()
                stream_url = data.get('stream_url', '').strip()
                camera_type = data.get('camera_type', 'ip').strip()
                description = data.get('description', 'Smart camera via QR setup')
                
                if not name or not stream_url:
                    return jsonify({
                        'status': 'error',
                        'message': 'Camera name and stream URL are required'
                    })
                
                # Add camera to Guardia AI
                camera_id, success, message = self.camera_manager.add_camera(
                    camera_type, stream_url, name, description
                )
                
                if success:
                    # Try to connect the camera
                    self.camera_manager.connect_all_cameras()
                    
                    response_data = {
                        'status': 'success',
                        'camera_id': camera_id,
                        'message': f'Camera "{name}" registered successfully!',
                        'guardia_info': {
                            'version': '1.0',
                            'features': ['face_recognition', 'object_detection', 'threat_analysis']
                        }
                    }
                    
                    if request.content_type == 'application/json':
                        return jsonify(response_data)
                    else:
                        return f"<h2>✅ Success!</h2><p>{response_data['message']}</p>"
                else:
                    error_response = {
                        'status': 'error',
                        'message': f'Failed to register camera: {message}'
                    }
                    
                    if request.content_type == 'application/json':
                        return jsonify(error_response)
                    else:
                        return f"<h2>❌ Error</h2><p>{error_response['message']}</p>"
                
            except Exception as e:
                error_response = {
                    'status': 'error',
                    'message': f'Registration failed: {str(e)}'
                }
                
                if request.content_type == 'application/json':
                    return jsonify(error_response)
                else:
                    return f"<h2>❌ Error</h2><p>{error_response['message']}</p>"
    
    def start_server(self):
        """Start the web server in a separate thread"""
        if not self.running:
            self.running = True
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host='0.0.0.0', 
                    port=self.port, 
                    debug=False, 
                    use_reloader=False
                )
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            return True
        return False
    
    def stop_server(self):
        """Stop the web server"""
        self.running = False
        # Note: Flask doesn't have a clean shutdown method
        # In a production environment, you'd use a proper WSGI server
