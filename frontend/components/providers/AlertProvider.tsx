"use client";

/**
 * Guardia AI — Alert Provider
 * ===========================
 * Manages the real-time WebSocket connection to the backend and
 * provides a global stream of surveillance events.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { APIEvent, api } from '@/lib/api-client';

interface AlertContextType {
  alerts: APIEvent[];
  isConnected: boolean;
  addAlert: (alert: APIEvent) => void;
  markAsReviewed: (id: string) => Promise<void>;
  recentAlerts: APIEvent[]; // Filtered or sorted
}

const AlertContext = createContext<AlertContextType | undefined>(undefined);

const WS_URL = 'ws://127.0.0.1:8000/ws/alerts';

export function AlertProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<APIEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  // Load initial events from DB
  useEffect(() => {
    api.getEvents().then(data => {
      setAlerts(data);
    }).catch(err => console.error("Failed to fetch initial events:", err));
  }, []);

  // Use a callback to handle incoming alerts to avoid stale state
  const addAlert = useCallback((alert: APIEvent) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50)); // Keep last 50
  }, []);

  const markAsReviewed = async (id: string) => {
    try {
      await api.markEventReviewed(id);
      setAlerts(prev => prev.map(a => a.event_id === id ? { ...a, is_reviewed: true } : a));
    } catch (err) {
      console.error("Failed to review event:", err);
    }
  };

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      console.log("Connecting to Guardia WS...");
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        setIsConnected(true);
        console.log("✅ WebSocket Connected");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ALERT') {
            addAlert(data.payload);
            // Optional: Play alert sound
          }
        } catch (err) {
          console.error("WS Message Error:", err);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        console.log("❌ WebSocket Disconnected. Retrying...");
        reconnectTimeout = setTimeout(connect, 3000); // Reconnect in 3s
      };

      socket.onerror = (err) => {
        console.error("WS Socket Error:", err);
        socket?.close();
      };
    };

    connect();

    return () => {
      socket?.close();
      clearTimeout(reconnectTimeout);
    };
  }, [addAlert]);

  return (
    <AlertContext.Provider value={{ 
      alerts, 
      isConnected, 
      addAlert, 
      markAsReviewed,
      recentAlerts: alerts.filter(a => !a.is_reviewed).slice(0, 10)
    }}>
      {children}
    </AlertContext.Provider>
  );
}

export function useAlerts() {
  const context = useContext(AlertContext);
  if (context === undefined) {
    throw new Error('useAlerts must be used within an AlertProvider');
  }
  return context;
}
