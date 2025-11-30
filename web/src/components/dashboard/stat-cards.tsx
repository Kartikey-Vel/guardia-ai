'use client'

import { useQuery } from '@tanstack/react-query'
import { eventsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, Activity, Shield, CheckCircle } from 'lucide-react'

export function StatCards() {
  const { data: events } = useQuery({
    queryKey: ['events', 'recent'],
    queryFn: () => eventsApi.list({ limit: 100 }),
  })

  const total = events?.data.total || 0
  const critical = events?.data.events.filter((e) => e.severity === 'critical').length || 0
  const acknowledged = events?.data.events.filter((e) => e.acknowledged).length || 0
  const unacknowledged = total - acknowledged

  const stats = [
    {
      title: 'Total Events',
      value: total,
      icon: Activity,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Critical Alerts',
      value: critical,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
    {
      title: 'Acknowledged',
      value: acknowledged,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Pending',
      value: unacknowledged,
      icon: Shield,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
    },
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon
        return (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <div className={`${stat.bgColor} p-2 rounded-md`}>
                <Icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
