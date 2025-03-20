'use client';

import { useState, useEffect, useCallback } from 'react';
import { get, post, put } from '@/utils/api';

export type ThreatLevel = {
  level: 'low' | 'medium' | 'high';
  score: number;
};

export type SecurityEvent = {
  event_id: string;
  event_type: string;
  description: string;
  threat_level: ThreatLevel;
  location: string;
  timestamp: string;
  video_clip_url?: string;
  audio_clip_url?: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
};

export type EventFilters = {
  event_type?: string;
  threat_level?: string;
  acknowledged?: boolean;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
};

export function useEvents(initialFilters: EventFilters = {}) {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<EventFilters>(initialFilters);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Convert filters to URL query params
      const params: Record<string, string> = {};
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params[key] = String(value);
        }
      });

      const { data, error } = await get<SecurityEvent[]>('events', params);

      if (error) {
        setError(error);
        return;
      }

      setEvents(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Acknowledge an event
  const acknowledgeEvent = async (eventId: string) => {
    try {
      const { data, error } = await put<SecurityEvent>(`events/${eventId}/acknowledge`);
      
      if (error) {
        throw new Error(error);
      }

      // Update the event in the local state
      setEvents((prevEvents) =>
        prevEvents.map((event) =>
          event.event_id === eventId ? { ...event, ...data } : event
        )
      );

      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge event');
      throw err;
    }
  };

  // Create a new event
  const createEvent = async (eventData: Omit<SecurityEvent, 'event_id'>) => {
    try {
      const { data, error } = await post<SecurityEvent>('events', eventData);
      
      if (error) {
        throw new Error(error);
      }

      // Add the new event to the local state
      setEvents((prevEvents) => [data!, ...prevEvents]);

      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create event');
      throw err;
    }
  };

  // Update filters
  const updateFilters = (newFilters: Partial<EventFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  // Fetch events when filters change
  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  return {
    events,
    loading,
    error,
    filters,
    updateFilters,
    acknowledgeEvent,
    createEvent,
    refreshEvents: fetchEvents,
  };
}
