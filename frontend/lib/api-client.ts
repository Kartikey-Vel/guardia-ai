/**
 * Guardia AI — API Client
 * =======================
 * Axios-based client for communicating with the FastAPI backend.
 */

import axios from 'axios';

// Backend URL — in production this should be an environment variable
// e.g., process.env.NEXT_PUBLIC_API_URL
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Types ---

export interface APIEvent {
  event_id: string;
  timestamp: string;
  camera_id: string;
  classification: string;
  severity: number;
  confidence: number;
  description: string;
  attribution: any;
  ai_model: string;
  is_reviewed: boolean;
}

export interface APICamera {
  camera_id: string;
  name: string;
  rtsp_url: string | null;
  zone: string;
  risk_level: number;
  is_active: boolean;
}

export interface AnalyticsSummary {
  total_events: number;
  reviewed_events: number;
  unreviewed_events: number;
  avg_severity: number;
  top_classification: string | null;
  cameras_active: number;
}

// --- API Methods ---

export const api = {
  // Events
  getEvents: () => apiClient.get<APIEvent[]>('/events').then(res => res.data),
  markEventReviewed: (id: string) => apiClient.patch(`/events/${id}/review`),
  
  // Cameras
  getCameras: () => apiClient.get<APICamera[]>('/cameras').then(res => res.data),
  toggleCamera: (id: string) => apiClient.post(`/cameras/${id}/toggle`),
  
  // Analytics
  getAnalyticsSummary: () => apiClient.get<AnalyticsSummary>('/analytics/summary').then(res => res.data),
  
  // Settings
  getSettings: () => apiClient.get('/settings').then(res => res.data),
  updateSettings: (data: any) => apiClient.patch('/settings', data).then(res => res.data),
  
  // System
  getStatus: () => apiClient.get('/status').then(res => res.data),
  triggerDemo: (scenario: string) => apiClient.post('/demo/trigger', { scenario }),
};
