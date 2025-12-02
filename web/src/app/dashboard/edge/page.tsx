'use client'

import { useEffect, useState } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { 
  Cpu, 
  HardDrive, 
  Wifi,
  WifiOff,
  Activity,
  Gauge,
  Cloud,
  CloudOff,
  Settings2,
  RefreshCw,
  Loader2,
  Check,
  X,
  Zap,
  MemoryStick
} from 'lucide-react'
import { edgeApi, type EdgeNode } from '@/lib/api'
import { toast } from 'sonner'

interface EdgeConfig {
  motion_threshold: number
  jpeg_quality: number
  enable_local_storage: boolean
  cloud_sync_enabled: boolean
  max_local_storage_gb: number
  frame_skip: number
}

export default function EdgePage() {
  const [nodes, setNodes] = useState<EdgeNode[]>([])
  const [bandwidth, setBandwidth] = useState<any>(null)
  const [storage, setStorage] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [config, setConfig] = useState<EdgeConfig>({
    motion_threshold: 0.3,
    jpeg_quality: 75,
    enable_local_storage: true,
    cloud_sync_enabled: true,
    max_local_storage_gb: 50,
    frame_skip: 2
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [nodesRes, bandwidthRes, storageRes] = await Promise.all([
        edgeApi.getNodes(),
        edgeApi.getBandwidth(),
        edgeApi.getStorage()
      ])
      setNodes(Array.isArray(nodesRes.data) ? nodesRes.data : [nodesRes.data])
      setBandwidth(bandwidthRes.data)
      setStorage(storageRes.data)
    } catch (error) {
      console.error('Failed to load edge data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    try {
      await edgeApi.updateConfig(config)
      toast.success('Configuration saved')
    } catch (error) {
      toast.error('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online':
        return <Badge className="bg-green-500"><Check className="h-3 w-3 mr-1" /> Online</Badge>
      case 'offline':
        return <Badge variant="destructive"><X className="h-3 w-3 mr-1" /> Offline</Badge>
      case 'degraded':
        return <Badge className="bg-yellow-500"><Activity className="h-3 w-3 mr-1" /> Degraded</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[calc(100vh-200px)]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Edge Computing</h1>
            <p className="text-muted-foreground">
              Monitor edge nodes and optimize bandwidth
            </p>
          </div>
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Overview Stats */}
        <div className="grid gap-6 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Cpu className="h-4 w-4" />
                CPU Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {nodes[0]?.cpu_usage?.toFixed(1) || 0}%
              </div>
              <Progress value={nodes[0]?.cpu_usage || 0} className="mt-2" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <MemoryStick className="h-4 w-4" />
                Memory Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {nodes[0]?.memory_usage?.toFixed(1) || 0}%
              </div>
              <Progress value={nodes[0]?.memory_usage || 0} className="mt-2" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Wifi className="h-4 w-4" />
                Bandwidth Saved
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">
                {bandwidth?.saved_mb?.toFixed(1) || 0} MB
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {bandwidth?.reduction_percent?.toFixed(0) || 0}% reduction
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <HardDrive className="h-4 w-4" />
                Local Storage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {formatBytes(storage?.used_bytes || 0)}
              </div>
              <Progress 
                value={((storage?.used_bytes || 0) / (storage?.total_bytes || 1)) * 100} 
                className="mt-2" 
              />
            </CardContent>
          </Card>
        </div>

        {/* Edge Nodes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Edge Nodes
            </CardTitle>
            <CardDescription>
              Local processing nodes and their status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Node</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>CPU</TableHead>
                  <TableHead>Memory</TableHead>
                  <TableHead>GPU</TableHead>
                  <TableHead>Processed Frames</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nodes.map((node, index) => (
                  <TableRow key={node.id || index}>
                    <TableCell className="font-medium">
                      {node.name || `Node ${index + 1}`}
                    </TableCell>
                    <TableCell>{getStatusBadge(node.status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={node.cpu_usage} className="w-16 h-2" />
                        <span className="text-sm">{node.cpu_usage?.toFixed(0)}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={node.memory_usage} className="w-16 h-2" />
                        <span className="text-sm">{node.memory_usage?.toFixed(0)}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {node.gpu_available ? (
                        <Badge className="bg-green-500">Available</Badge>
                      ) : (
                        <Badge variant="secondary">N/A</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {node.processed_frames?.toLocaleString() || 0}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-5 w-5" />
              Edge Configuration
            </CardTitle>
            <CardDescription>
              Optimize edge processing and bandwidth usage
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Motion Threshold */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Motion Detection Threshold</Label>
                  <span className="text-sm text-muted-foreground">
                    {(config.motion_threshold * 100).toFixed(0)}%
                  </span>
                </div>
                <Slider
                  value={[config.motion_threshold * 100]}
                  onValueChange={([value]) => setConfig({ ...config, motion_threshold: value / 100 })}
                  max={100}
                  step={5}
                />
                <p className="text-xs text-muted-foreground">
                  Higher values = less sensitive motion detection
                </p>
              </div>

              {/* JPEG Quality */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>JPEG Compression Quality</Label>
                  <span className="text-sm text-muted-foreground">
                    {config.jpeg_quality}%
                  </span>
                </div>
                <Slider
                  value={[config.jpeg_quality]}
                  onValueChange={([value]) => setConfig({ ...config, jpeg_quality: value })}
                  min={30}
                  max={100}
                  step={5}
                />
                <p className="text-xs text-muted-foreground">
                  Lower values = smaller files, lower quality
                </p>
              </div>

              {/* Frame Skip */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Frame Skip Rate</Label>
                  <span className="text-sm text-muted-foreground">
                    Process 1 of every {config.frame_skip} frames
                  </span>
                </div>
                <Slider
                  value={[config.frame_skip]}
                  onValueChange={([value]) => setConfig({ ...config, frame_skip: value })}
                  min={1}
                  max={10}
                  step={1}
                />
                <p className="text-xs text-muted-foreground">
                  Higher values = lower CPU usage, less real-time
                </p>
              </div>

              {/* Max Local Storage */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Max Local Storage</Label>
                  <span className="text-sm text-muted-foreground">
                    {config.max_local_storage_gb} GB
                  </span>
                </div>
                <Slider
                  value={[config.max_local_storage_gb]}
                  onValueChange={([value]) => setConfig({ ...config, max_local_storage_gb: value })}
                  min={10}
                  max={500}
                  step={10}
                />
              </div>
            </div>

            <div className="flex gap-6">
              {/* Local Storage Toggle */}
              <div className="flex items-center gap-3">
                <Switch
                  checked={config.enable_local_storage}
                  onCheckedChange={(checked) => setConfig({ ...config, enable_local_storage: checked })}
                />
                <div>
                  <Label>Local Storage</Label>
                  <p className="text-xs text-muted-foreground">
                    Store critical footage locally
                  </p>
                </div>
              </div>

              {/* Cloud Sync Toggle */}
              <div className="flex items-center gap-3">
                <Switch
                  checked={config.cloud_sync_enabled}
                  onCheckedChange={(checked) => setConfig({ ...config, cloud_sync_enabled: checked })}
                />
                <div>
                  <Label>Cloud Sync</Label>
                  <p className="text-xs text-muted-foreground">
                    Sync events to cloud storage
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Button onClick={handleSaveConfig} disabled={saving}>
                {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Save Configuration
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Bandwidth Optimization Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5" />
              Bandwidth Optimization
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-3">
              <div className="text-center p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Original Bandwidth</p>
                <p className="text-2xl font-bold">
                  {((bandwidth?.original_bps || 0) / 1024 / 1024).toFixed(1)} Mbps
                </p>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Optimized Bandwidth</p>
                <p className="text-2xl font-bold text-green-500">
                  {((bandwidth?.optimized_bps || 0) / 1024 / 1024).toFixed(1)} Mbps
                </p>
              </div>
              <div className="text-center p-4 border rounded-lg bg-green-500/10">
                <p className="text-sm text-muted-foreground mb-2">Savings</p>
                <p className="text-2xl font-bold text-green-500">
                  {bandwidth?.reduction_percent?.toFixed(0) || 0}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
