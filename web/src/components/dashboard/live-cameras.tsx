'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Video, Circle } from 'lucide-react'

const cameras = [
  { id: 'cam_front', name: 'Front Entrance', status: 'online' },
  { id: 'cam_parking', name: 'Parking Lot', status: 'online' },
  { id: 'cam_back', name: 'Back Exit', status: 'online' },
  { id: 'cam_lobby', name: 'Lobby', status: 'offline' },
]

export function LiveCameras() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {cameras.map((camera) => (
        <Card key={camera.id}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">
                {camera.name}
              </CardTitle>
              <div className="flex items-center space-x-1">
                <Circle
                  className={`h-2 w-2 fill-current ${
                    camera.status === 'online'
                      ? 'text-green-500'
                      : 'text-red-500'
                  }`}
                />
                <span className="text-xs text-muted-foreground">
                  {camera.status}
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="aspect-video bg-gray-900 rounded-md flex items-center justify-center">
              {camera.status === 'online' ? (
                <div className="text-white text-sm">
                  <Video className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p className="opacity-50">Live Feed</p>
                  <p className="text-xs opacity-30 mt-1">{camera.id}</p>
                </div>
              ) : (
                <div className="text-white text-sm opacity-50">
                  <Video className="h-12 w-12 mx-auto mb-2" />
                  <p>Camera Offline</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
