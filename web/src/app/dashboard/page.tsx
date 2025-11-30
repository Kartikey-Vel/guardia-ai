'use client'

import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { EventTimeline } from '@/components/dashboard/event-timeline'
import { LiveCameras } from '@/components/dashboard/live-cameras'
import { StatCards } from '@/components/dashboard/stat-cards'
import { EventChart } from '@/components/dashboard/event-chart'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Security Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time monitoring and event management
          </p>
        </div>

        <StatCards />

        <Tabs defaultValue="timeline" className="space-y-4">
          <TabsList>
            <TabsTrigger value="timeline">Event Timeline</TabsTrigger>
            <TabsTrigger value="cameras">Live Cameras</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="timeline" className="space-y-4">
            <EventTimeline />
          </TabsContent>

          <TabsContent value="cameras" className="space-y-4">
            <LiveCameras />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <EventChart />
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}
