'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  Camera, 
  Plus, 
  RefreshCw, 
  Trash2, 
  Wifi, 
  WifiOff,
  Smartphone,
  Monitor,
  Settings2,
  AlertCircle,
  CheckCircle2,
  Loader2
} from 'lucide-react'
import { cameraApi, type Camera as CameraType } from '@/lib/api'
import { toast } from 'sonner'

export default function CamerasPage() {
  const [cameras, setCameras] = useState<CameraType[]>([])
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [discoveredDevices, setDiscoveredDevices] = useState<any[]>([])
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [newCamera, setNewCamera] = useState({
    name: '',
    type: 'webcam' as 'webcam' | 'droidcam' | 'rtsp' | 'usb',
    url: '',
    priority: 1
  })

  useEffect(() => {
    loadCameras()
    const interval = setInterval(loadCameras, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadCameras = async () => {
    try {
      const response = await cameraApi.list()
      setCameras(response.data)
    } catch (error) {
      console.error('Failed to load cameras:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDiscoverDroidCam = async () => {
    setDiscovering(true)
    try {
      const response = await cameraApi.discoverDroidCam()
      setDiscoveredDevices(response.data || [])
      if (response.data?.length === 0) {
        toast.info('No DroidCam devices found on the network')
      } else {
        toast.success(`Found ${response.data.length} DroidCam device(s)`)
      }
    } catch (error) {
      toast.error('Failed to discover DroidCam devices')
    } finally {
      setDiscovering(false)
    }
  }

  const handleAddCamera = async () => {
    try {
      await cameraApi.add(newCamera)
      toast.success('Camera added successfully')
      setAddDialogOpen(false)
      setNewCamera({ name: '', type: 'webcam', url: '', priority: 1 })
      loadCameras()
    } catch (error) {
      toast.error('Failed to add camera')
    }
  }

  const handleReconnect = async (cameraId: string) => {
    try {
      await cameraApi.reconnect(cameraId)
      toast.success('Reconnecting to camera...')
      loadCameras()
    } catch (error) {
      toast.error('Failed to reconnect')
    }
  }

  const handleRemove = async (cameraId: string) => {
    if (!confirm('Are you sure you want to remove this camera?')) return
    try {
      await cameraApi.remove(cameraId)
      toast.success('Camera removed')
      loadCameras()
    } catch (error) {
      toast.error('Failed to remove camera')
    }
  }

  const getCameraIcon = (type: string) => {
    switch (type) {
      case 'droidcam': return <Smartphone className="h-5 w-5" />
      case 'webcam': return <Monitor className="h-5 w-5" />
      default: return <Camera className="h-5 w-5" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" /> Active</Badge>
      case 'inactive':
        return <Badge variant="secondary"><WifiOff className="h-3 w-3 mr-1" /> Inactive</Badge>
      case 'error':
        return <Badge variant="destructive"><AlertCircle className="h-3 w-3 mr-1" /> Error</Badge>
      case 'reconnecting':
        return <Badge className="bg-yellow-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Reconnecting</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Camera Management</h1>
            <p className="text-muted-foreground">
              Configure and monitor your camera feeds
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleDiscoverDroidCam} disabled={discovering}>
              {discovering ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Smartphone className="h-4 w-4 mr-2" />}
              Discover DroidCam
            </Button>
            <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Camera
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New Camera</DialogTitle>
                  <DialogDescription>
                    Configure a new camera source for monitoring
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Camera Name</Label>
                    <Input
                      id="name"
                      value={newCamera.name}
                      onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                      placeholder="Living Room Camera"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="type">Camera Type</Label>
                    <Select
                      value={newCamera.type}
                      onValueChange={(value: any) => setNewCamera({ ...newCamera, type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select camera type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="webcam">Webcam (Built-in)</SelectItem>
                        <SelectItem value="droidcam">DroidCam (Android)</SelectItem>
                        <SelectItem value="rtsp">RTSP Stream</SelectItem>
                        <SelectItem value="usb">USB Camera</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {(newCamera.type === 'droidcam' || newCamera.type === 'rtsp') && (
                    <div className="space-y-2">
                      <Label htmlFor="url">Camera URL/IP</Label>
                      <Input
                        id="url"
                        value={newCamera.url}
                        onChange={(e) => setNewCamera({ ...newCamera, url: e.target.value })}
                        placeholder={newCamera.type === 'droidcam' ? '192.168.1.100:4747' : 'rtsp://...'}
                      />
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="priority">Priority (1-10)</Label>
                    <Input
                      id="priority"
                      type="number"
                      min={1}
                      max={10}
                      value={newCamera.priority}
                      onChange={(e) => setNewCamera({ ...newCamera, priority: parseInt(e.target.value) })}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setAddDialogOpen(false)}>Cancel</Button>
                  <Button onClick={handleAddCamera}>Add Camera</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Discovered DroidCam Devices */}
        {discoveredDevices.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5" />
                Discovered DroidCam Devices
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {discoveredDevices.map((device, index) => (
                  <Card key={index} className="border-dashed">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{device.name || `Device ${index + 1}`}</p>
                          <p className="text-sm text-muted-foreground">{device.ip}:{device.port}</p>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => {
                            setNewCamera({
                              name: device.name || `DroidCam ${index + 1}`,
                              type: 'droidcam',
                              url: `${device.ip}:${device.port}`,
                              priority: 1
                            })
                            setAddDialogOpen(true)
                          }}
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Camera Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : cameras.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center h-64">
              <Camera className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No Cameras Configured</h3>
              <p className="text-muted-foreground mb-4">Add your first camera to start monitoring</p>
              <Button onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Camera
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {cameras.map((camera) => (
              <Card key={camera.id} className={camera.status === 'error' ? 'border-destructive' : ''}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getCameraIcon(camera.type)}
                      <CardTitle className="text-lg">{camera.name}</CardTitle>
                    </div>
                    {getStatusBadge(camera.status)}
                  </div>
                  <CardDescription>
                    {camera.type.toUpperCase()} • Priority {camera.priority}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {/* Camera Preview Placeholder */}
                  <div className="aspect-video bg-muted rounded-md mb-4 flex items-center justify-center">
                    {camera.status === 'active' ? (
                      <div className="text-center">
                        <Camera className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">Live Feed</p>
                      </div>
                    ) : (
                      <div className="text-center">
                        <WifiOff className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">No Signal</p>
                      </div>
                    )}
                  </div>

                  {/* Camera Stats */}
                  <div className="grid grid-cols-2 gap-2 text-sm mb-4">
                    <div>
                      <p className="text-muted-foreground">Resolution</p>
                      <p className="font-medium">{camera.resolution?.width}x{camera.resolution?.height}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">FPS</p>
                      <p className="font-medium">{camera.fps}</p>
                    </div>
                  </div>

                  {camera.error_message && (
                    <div className="bg-destructive/10 text-destructive text-sm p-2 rounded-md mb-4">
                      {camera.error_message}
                    </div>
                  )}

                  {/* Camera Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleReconnect(camera.id)}
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Reconnect
                    </Button>
                    <Button variant="outline" size="sm">
                      <Settings2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleRemove(camera.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Camera Statistics */}
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Cameras
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{cameras.length}</div>
              <p className="text-sm text-muted-foreground">
                {cameras.filter(c => c.status === 'active').length} active
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                DroidCam Devices
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {cameras.filter(c => c.type === 'droidcam').length}
              </div>
              <p className="text-sm text-muted-foreground">Mobile cameras connected</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Camera Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">
                {cameras.length > 0
                  ? Math.round((cameras.filter(c => c.status === 'active').length / cameras.length) * 100)
                  : 0}%
              </div>
              <p className="text-sm text-muted-foreground">Uptime rate</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}
