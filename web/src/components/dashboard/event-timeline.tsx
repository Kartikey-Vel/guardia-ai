'use client'

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { eventsApi, type Event } from '@/lib/api'
import { useWebSocketStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { formatRelativeTime, getSeverityColor, getEventClassLabel } from '@/lib/utils'
import { Check, ExternalLink } from 'lucide-react'

export function EventTimeline() {
  const queryClient = useQueryClient()
  const { events: wsEvents, connect, disconnect } = useWebSocketStore()
  const [filter, setFilter] = useState<string>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['events', filter],
    queryFn: () =>
      eventsApi.list({
        limit: 50,
        severity: filter === 'all' ? undefined : filter,
      }),
  })

  const acknowledgeMutation = useMutation({
    mutationFn: (eventId: string) => eventsApi.acknowledge(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
  })

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  const events = data?.data.events || []

  const severityFilters = ['all', 'critical', 'high', 'medium', 'low']

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Recent Events</CardTitle>
          <div className="flex space-x-2">
            {severityFilters.map((severity) => (
              <Button
                key={severity}
                variant={filter === severity ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter(severity)}
              >
                {severity.charAt(0).toUpperCase() + severity.slice(1)}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading events...
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No events found
          </div>
        ) : (
          <div className="space-y-4">
            {events.map((event: Event) => (
              <div
                key={event.id}
                className={`p-4 rounded-lg border ${getSeverityColor(event.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="font-semibold">
                        {getEventClassLabel(event.event_class)}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full border">
                        {event.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {event.camera_id}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      Confidence: {(event.confidence * 100).toFixed(1)}% •{' '}
                      {formatRelativeTime(event.timestamp)}
                    </p>
                    {event.acknowledged && (
                      <p className="text-xs text-green-600">
                        ✓ Acknowledged by {event.acknowledged_by}
                      </p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    {event.clip_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        asChild
                      >
                        <a
                          href={event.clip_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                    {!event.acknowledged && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => acknowledgeMutation.mutate(event.event_id)}
                        disabled={acknowledgeMutation.isPending}
                      >
                        <Check className="h-4 w-4 mr-1" />
                        Acknowledge
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
