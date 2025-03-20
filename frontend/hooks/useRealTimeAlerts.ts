"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "./useAuth";

export type SecurityAlert = {
  type: string;
  event_type: string;
  description: string;
  threat_level: {
    level: "low" | "medium" | "high";
    score: number;
  };
  location: string;
  event_id?: string;
  timestamp?: string;
  broadcast_time?: string;
};

export function useRealTimeAlerts() {
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, user } = useAuth();
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated || socketRef.current) return;

    const clientId = user?.username || `anonymous-${Date.now()}`;

    // Ensure WS_URL is properly formatted
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const wsEndpoint = `${wsUrl.replace(/\/$/, "")}/notify/ws/${clientId}`;

    try {
      const socket = new WebSocket(wsEndpoint);

      socket.onopen = () => {
        setConnected(true);
        setError(null);
        console.log("WebSocket connected");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle security alerts
          if (data.type === "security_alert") {
            setAlerts((prev) => [data, ...prev].slice(0, 50)); // Keep last 50 alerts
          }

          // Handle event acknowledgments
          if (data.type === "event_acknowledged") {
            // You can handle acknowledgment updates here
            console.log("Event acknowledged:", data);
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      socket.onerror = (event) => {
        setError("WebSocket connection error");
        setConnected(false);
        console.error("WebSocket error:", event);
      };

      socket.onclose = (event) => {
        setConnected(false);
        socketRef.current = null;
        console.log(`WebSocket disconnected: ${event.code} ${event.reason}`);

        // Clear any existing reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        // Attempt to reconnect after delay if not a normal closure
        if (event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isAuthenticated) connect();
            reconnectTimeoutRef.current = null;
          }, 5000);
        }
      };

      socketRef.current = socket;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to WebSocket"
      );
      setConnected(false);
    }
  }, [isAuthenticated, user]);

  // Clear alerts
  const clearAlerts = () => {
    setAlerts([]);
  };

  // Send a message to the WebSocket server
  const sendMessage = (message: unknown) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setError("WebSocket not connected");
      return false;
    }

    try {
      socketRef.current.send(JSON.stringify(message));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      return false;
    }
  };

  // Connect/disconnect based on authentication
  useEffect(() => {
    if (isAuthenticated) {
      connect();
    } else {
      // Disconnect if user logs out
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }

      // Clear any reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      setConnected(false);
    }

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [isAuthenticated, connect]);

  return {
    alerts,
    connected,
    error,
    clearAlerts,
    sendMessage,
  };
}
