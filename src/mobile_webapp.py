"""
Mobile-responsive web components and Progressive Web App (PWA) support for Guardia-AI.
Provides responsive dashboard, offline capabilities, and mobile notifications.
"""

import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MobileWebApp:
    """Mobile web app configuration and utilities"""
    
    def __init__(self):
        self.app_name = "Guardia-AI"
        self.app_short_name = "Guardia"
        self.app_description = "Real-time AI security monitoring system"
        self.theme_color = "#1f2937"
        self.background_color = "#0b0f14"
    
    def get_pwa_manifest(self) -> Dict[str, Any]:
        """Generate PWA manifest"""
        return {
            "name": self.app_name,
            "short_name": self.app_short_name,
            "description": self.app_description,
            "start_url": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "theme_color": self.theme_color,
            "background_color": self.background_color,
            "icons": [
                {
                    "src": "/static/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/static/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ],
            "categories": ["security", "monitoring", "productivity"],
            "lang": "en",
            "dir": "ltr"
        }
    
    def get_mobile_responsive_css(self) -> str:
        """Generate mobile-responsive CSS"""
        return """
        /* Mobile-First Responsive Design */
        
        /* Base mobile styles (320px and up) */
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 0;
            background: #0b0f14;
            color: #eaecef;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 8px;
        }
        
        /* Header */
        .header {
            background: #1f2937;
            padding: 12px 16px;
            border-bottom: 1px solid #374151;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .header h1 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #eaecef;
        }
        
        .header .status {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 2px;
        }
        
        /* Auth section */
        .auth {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin-top: 8px;
            width: 100%;
        }
        
        .auth input {
            flex: 1;
            min-width: 120px;
            padding: 8px;
            border: 1px solid #374151;
            background: #1f2937;
            color: #eaecef;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .auth button {
            padding: 8px 12px;
            background: #3b82f6;
            border: none;
            color: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            white-space: nowrap;
        }
        
        .auth button:hover {
            background: #2563eb;
        }
        
        /* Main content */
        .main-content {
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding: 16px 8px;
        }
        
        /* Video stream */
        .video-container {
            background: #1f2937;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }
        
        .video-container img {
            width: 100%;
            height: auto;
            display: block;
            max-height: 60vh;
            object-fit: contain;
        }
        
        .video-overlay {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        /* Cards */
        .card {
            background: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        
        .card h3 {
            margin: 0 0 12px 0;
            font-size: 16px;
            color: #f9fafb;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-icon {
            width: 20px;
            height: 20px;
            display: inline-block;
        }
        
        /* Metrics grid */
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .metric {
            background: #374151;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }
        
        .metric .label {
            color: #9ca3af;
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .metric .value {
            font-size: 18px;
            font-weight: 700;
            color: #eaecef;
        }
        
        /* Events list */
        .events {
            max-height: 300px;
            overflow-y: auto;
            -webkit-overflow-scrolling: touch;
        }
        
        .event {
            border-left: 4px solid #6b7280;
            padding: 12px;
            margin-bottom: 8px;
            background: #374151;
            border-radius: 0 4px 4px 0;
        }
        
        .event.harmful {
            border-left-color: #ef4444;
        }
        
        .event.trusted {
            border-left-color: #10b981;
        }
        
        .event-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
            flex-wrap: wrap;
            gap: 4px;
        }
        
        .event-time {
            font-size: 11px;
            color: #9ca3af;
        }
        
        .event-badge {
            background: #4b5563;
            color: #eaecef;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 500;
        }
        
        .event-badge.harmful {
            background: #ef4444;
        }
        
        .event-content {
            font-size: 13px;
            line-height: 1.4;
        }
        
        /* Setup section */
        .setup {
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        }
        
        .setup input, .setup textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #4b5563;
            background: #374151;
            color: #eaecef;
            border-radius: 4px;
            margin-bottom: 12px;
            font-size: 14px;
        }
        
        .setup textarea {
            height: 80px;
            resize: vertical;
        }
        
        .setup button {
            width: 100%;
            padding: 12px;
            background: #059669;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
            cursor: pointer;
        }
        
        .setup button:hover {
            background: #047857;
        }
        
        .setup button:disabled {
            background: #6b7280;
            cursor: not-allowed;
        }
        
        /* Jobs list */
        .jobs-list {
            font-size: 13px;
        }
        
        .job-item {
            background: #374151;
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
        }
        
        .job-status {
            font-weight: 500;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            text-transform: uppercase;
        }
        
        .job-status.queued { background: #fbbf24; color: #000; }
        .job-status.running { background: #3b82f6; color: #fff; }
        .job-status.completed { background: #10b981; color: #fff; }
        .job-status.failed { background: #ef4444; color: #fff; }
        
        /* Summary */
        .summary {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 12px;
            font-size: 13px;
            line-height: 1.5;
            color: #cbd5e1;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 16px;
            color: #6b7280;
            font-size: 12px;
            border-top: 1px solid #374151;
            margin-top: 24px;
        }
        
        /* Utility classes */
        .text-center { text-align: center; }
        .text-sm { font-size: 12px; }
        .text-xs { font-size: 11px; }
        .font-bold { font-weight: 700; }
        .mb-2 { margin-bottom: 8px; }
        .mb-4 { margin-bottom: 16px; }
        .mt-2 { margin-top: 8px; }
        .mt-4 { margin-top: 16px; }
        
        /* Loading states */
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            margin: -10px 0 0 -10px;
            border: 2px solid #3b82f6;
            border-radius: 50%;
            border-top-color: transparent;
            animation: loading-spinner 1s linear infinite;
        }
        
        @keyframes loading-spinner {
            to { transform: rotate(360deg); }
        }
        
        /* Tablet styles (768px and up) */
        @media screen and (min-width: 768px) {
            .container {
                padding: 16px;
            }
            
            .header {
                padding: 16px 24px;
            }
            
            .header h1 {
                font-size: 24px;
            }
            
            .auth {
                width: auto;
                margin-top: 0;
            }
            
            .main-content {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 24px;
                padding: 24px 16px;
            }
            
            .video-container img {
                max-height: 70vh;
            }
            
            .metrics {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            }
            
            .card {
                padding: 20px;
            }
            
            .events {
                max-height: 400px;
            }
        }
        
        /* Desktop styles (1024px and up) */
        @media screen and (min-width: 1024px) {
            .container {
                max-width: 1200px;
                padding: 20px;
            }
            
            .main-content {
                gap: 32px;
                padding: 32px 20px;
            }
            
            .metrics {
                grid-template-columns: repeat(4, 1fr);
            }
            
            .video-container img {
                max-height: 80vh;
            }
        }
        
        /* Large desktop styles (1280px and up) */
        @media screen and (min-width: 1280px) {
            .container {
                max-width: 1400px;
            }
            
            .main-content {
                grid-template-columns: 3fr 2fr;
            }
        }
        
        /* Dark mode enhancements */
        @media (prefers-color-scheme: dark) {
            body {
                background: #0b0f14;
                color: #eaecef;
            }
        }
        
        /* High contrast mode */
        @media (prefers-contrast: high) {
            .card {
                border-width: 2px;
            }
            
            .metric {
                border: 1px solid #6b7280;
            }
        }
        
        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* Print styles */
        @media print {
            .header,
            .footer,
            .setup,
            .auth {
                display: none;
            }
            
            .main-content {
                display: block;
            }
            
            .card {
                border: 1px solid #000;
                page-break-inside: avoid;
            }
        }
        
        /* Touch-friendly enhancements */
        @media (pointer: coarse) {
            button,
            input,
            .metric {
                min-height: 44px;
            }
            
            .event {
                padding: 16px;
            }
        }
        """
    
    def get_service_worker_js(self) -> str:
        """Generate service worker for offline functionality"""
        return """
        const CACHE_NAME = 'guardia-ai-v1';
        const urlsToCache = [
            '/',
            '/static/css/mobile.css',
            '/static/js/mobile.js',
            '/static/icons/icon-192.png',
            '/static/icons/icon-512.png'
        ];
        
        // Install event
        self.addEventListener('install', function(event) {
            event.waitUntil(
                caches.open(CACHE_NAME)
                    .then(function(cache) {
                        return cache.addAll(urlsToCache);
                    })
            );
        });
        
        // Fetch event
        self.addEventListener('fetch', function(event) {
            event.respondWith(
                caches.match(event.request)
                    .then(function(response) {
                        // Return cached version or fetch from network
                        return response || fetch(event.request);
                    })
            );
        });
        
        // Push notification handling
        self.addEventListener('push', function(event) {
            if (event.data) {
                const options = {
                    body: event.data.text(),
                    icon: '/static/icons/icon-192.png',
                    badge: '/static/icons/badge-72.png',
                    vibrate: [100, 50, 100],
                    data: {
                        dateOfArrival: Date.now(),
                        primaryKey: 1
                    },
                    actions: [
                        {
                            action: 'explore',
                            title: 'View Dashboard',
                            icon: '/static/icons/view-icon.png'
                        },
                        {
                            action: 'close',
                            title: 'Dismiss',
                            icon: '/static/icons/close-icon.png'
                        }
                    ]
                };
                
                event.waitUntil(
                    self.registration.showNotification('Guardia-AI Alert', options)
                );
            }
        });
        
        // Notification click handling
        self.addEventListener('notificationclick', function(event) {
            event.notification.close();
            
            if (event.action === 'explore') {
                event.waitUntil(
                    clients.openWindow('/')
                );
            }
        });
        """
    
    def get_mobile_js(self) -> str:
        """Generate mobile-specific JavaScript"""
        return """
        // Mobile app functionality
        class MobileApp {
            constructor() {
                this.isOnline = navigator.onLine;
                this.installPrompt = null;
                this.isStandalone = window.matchMedia('(display-mode: standalone)').matches;
                
                this.init();
            }
            
            init() {
                // Register service worker
                if ('serviceWorker' in navigator) {
                    navigator.serviceWorker.register('/sw.js')
                        .then(registration => {
                            console.log('Service Worker registered:', registration);
                        })
                        .catch(error => {
                            console.log('Service Worker registration failed:', error);
                        });
                }
                
                // Handle install prompt
                window.addEventListener('beforeinstallprompt', (e) => {
                    e.preventDefault();
                    this.installPrompt = e;
                    this.showInstallBanner();
                });
                
                // Handle online/offline status
                window.addEventListener('online', () => {
                    this.isOnline = true;
                    this.updateConnectivityStatus();
                });
                
                window.addEventListener('offline', () => {
                    this.isOnline = false;
                    this.updateConnectivityStatus();
                });
                
                // Handle orientation changes
                window.addEventListener('orientationchange', () => {
                    setTimeout(() => {
                        this.handleOrientationChange();
                    }, 100);
                });
                
                // Touch gestures
                this.initTouchGestures();
                
                // Request notification permission
                this.requestNotificationPermission();
                
                // Initial connectivity status
                this.updateConnectivityStatus();
            }
            
            showInstallBanner() {
                if (!this.isStandalone && this.installPrompt) {
                    const banner = document.createElement('div');
                    banner.className = 'install-banner';
                    banner.innerHTML = `
                        <div style="background: #3b82f6; color: white; padding: 12px; text-align: center; position: fixed; top: 0; left: 0; right: 0; z-index: 1000;">
                            <span>Install Guardia-AI for better experience</span>
                            <button onclick="mobileApp.installApp()" style="margin-left: 12px; background: white; color: #3b82f6; border: none; padding: 4px 8px; border-radius: 3px;">Install</button>
                            <button onclick="this.parentElement.remove()" style="margin-left: 8px; background: transparent; color: white; border: 1px solid white; padding: 4px 8px; border-radius: 3px;">Later</button>
                        </div>
                    `;
                    document.body.prepend(banner);
                }
            }
            
            async installApp() {
                if (this.installPrompt) {
                    this.installPrompt.prompt();
                    const result = await this.installPrompt.userChoice;
                    console.log('Install prompt result:', result);
                    this.installPrompt = null;
                    
                    // Remove banner
                    const banner = document.querySelector('.install-banner');
                    if (banner) banner.remove();
                }
            }
            
            updateConnectivityStatus() {
                const statusElement = document.querySelector('.connectivity-status');
                if (!statusElement) {
                    // Create status indicator
                    const status = document.createElement('div');
                    status.className = 'connectivity-status';
                    status.style.cssText = `
                        position: fixed; 
                        top: 60px; 
                        right: 16px; 
                        padding: 4px 8px; 
                        border-radius: 3px; 
                        font-size: 11px; 
                        z-index: 999;
                        transition: all 0.3s ease;
                    `;
                    document.body.appendChild(status);
                }
                
                const status = document.querySelector('.connectivity-status');
                if (this.isOnline) {
                    status.textContent = 'Online';
                    status.style.background = '#10b981';
                    status.style.color = 'white';
                } else {
                    status.textContent = 'Offline';
                    status.style.background = '#ef4444';
                    status.style.color = 'white';
                }
                
                // Auto-hide after 3 seconds if online
                if (this.isOnline) {
                    setTimeout(() => {
                        status.style.opacity = '0';
                        setTimeout(() => status.remove(), 300);
                    }, 3000);
                }
            }
            
            handleOrientationChange() {
                // Refresh video stream on orientation change
                const videoImg = document.querySelector('.video-container img');
                if (videoImg) {
                    const src = videoImg.src;
                    videoImg.src = '';
                    setTimeout(() => {
                        videoImg.src = src;
                    }, 100);
                }
            }
            
            initTouchGestures() {
                let touchStartY = 0;
                let touchEndY = 0;
                
                document.addEventListener('touchstart', (e) => {
                    touchStartY = e.changedTouches[0].screenY;
                });
                
                document.addEventListener('touchend', (e) => {
                    touchEndY = e.changedTouches[0].screenY;
                    this.handleGesture();
                });
                
                const handleGesture = () => {
                    const swipeThreshold = 50;
                    const diff = touchStartY - touchEndY;
                    
                    if (Math.abs(diff) > swipeThreshold) {
                        if (diff > 0) {
                            // Swipe up - refresh data
                            if (typeof refresh === 'function') {
                                this.showRefreshFeedback();
                                refresh();
                            }
                        }
                    }
                };
                
                this.handleGesture = handleGesture;
            }
            
            showRefreshFeedback() {
                const feedback = document.createElement('div');
                feedback.textContent = 'Refreshing...';
                feedback.style.cssText = `
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(59, 130, 246, 0.9);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    z-index: 9999;
                    font-size: 14px;
                `;
                
                document.body.appendChild(feedback);
                
                setTimeout(() => {
                    feedback.remove();
                }, 1500);
            }
            
            async requestNotificationPermission() {
                if ('Notification' in window && 'serviceWorker' in navigator) {
                    const permission = await Notification.requestPermission();
                    console.log('Notification permission:', permission);
                    
                    if (permission === 'granted') {
                        this.setupPushNotifications();
                    }
                }
            }
            
            async setupPushNotifications() {
                try {
                    const registration = await navigator.serviceWorker.ready;
                    const subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: this.urlBase64ToUint8Array(
                            'YOUR_VAPID_PUBLIC_KEY' // Replace with actual VAPID key
                        )
                    });
                    
                    // Send subscription to server
                    await fetch('/api/push-subscription', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(subscription)
                    });
                } catch (error) {
                    console.error('Failed to setup push notifications:', error);
                }
            }
            
            urlBase64ToUint8Array(base64String) {
                const padding = '='.repeat((4 - base64String.length % 4) % 4);
                const base64 = (base64String + padding)
                    .replace(/-/g, '+')
                    .replace(/_/g, '/');
                
                const rawData = window.atob(base64);
                const outputArray = new Uint8Array(rawData.length);
                
                for (let i = 0; i < rawData.length; ++i) {
                    outputArray[i] = rawData.charCodeAt(i);
                }
                return outputArray;
            }
            
            // Utility methods for mobile experience
            vibrate(pattern = [100]) {
                if ('vibrate' in navigator) {
                    navigator.vibrate(pattern);
                }
            }
            
            showToast(message, type = 'info') {
                const toast = document.createElement('div');
                toast.textContent = message;
                toast.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    padding: 12px 20px;
                    border-radius: 6px;
                    color: white;
                    font-size: 14px;
                    z-index: 9999;
                    max-width: 80%;
                    text-align: center;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                `;
                
                const colors = {
                    'info': '#3b82f6',
                    'success': '#10b981',
                    'warning': '#f59e0b',
                    'error': '#ef4444'
                };
                
                toast.style.background = colors[type] || colors.info;
                document.body.appendChild(toast);
                
                // Animate in
                setTimeout(() => {
                    toast.style.opacity = '1';
                }, 10);
                
                // Auto remove
                setTimeout(() => {
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                }, 3000);
            }
        }
        
        // Initialize mobile app
        const mobileApp = new MobileApp();
        
        // Enhanced refresh function for mobile
        const originalRefresh = window.refresh;
        window.refresh = function() {
            if (!navigator.onLine) {
                mobileApp.showToast('Device is offline', 'warning');
                return;
            }
            
            if (originalRefresh) {
                originalRefresh();
            }
        };
        
        // Mobile-specific event handlers
        document.addEventListener('DOMContentLoaded', function() {
            // Add loading states to buttons
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {
                button.addEventListener('click', function() {
                    if (!this.disabled) {
                        this.classList.add('loading');
                        setTimeout(() => {
                            this.classList.remove('loading');
                        }, 1000);
                    }
                });
            });
            
            // Optimize images for mobile
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                img.addEventListener('load', function() {
                    this.style.opacity = '1';
                });
                
                img.addEventListener('error', function() {
                    this.style.background = '#374151';
                    this.style.color = '#9ca3af';
                    this.alt = 'Failed to load';
                });
                
                // Start with opacity 0 for smooth loading
                img.style.opacity = '0';
                img.style.transition = 'opacity 0.3s ease';
            });
        });
        """

# Global mobile web app instance
mobile_webapp = MobileWebApp()
