'use client'

import { useEffect, useState, useRef } from 'react'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'
import { 
  Shield, 
  ShieldAlert, 
  ShieldCheck,
  User,
  Users,
  UserPlus,
  Camera,
  AlertTriangle,
  Eye,
  EyeOff,
  Trash2,
  Upload,
  Clock,
  Activity,
  Loader2,
  Home
} from 'lucide-react'
import { 
  securityApi, 
  type SecurityStatus, 
  type TrackedPerson, 
  type EnrolledFace 
} from '@/lib/api'
import { toast } from 'sonner'

export default function SecurityPage() {
  const [status, setStatus] = useState<SecurityStatus | null>(null)
  const [persons, setPersons] = useState<TrackedPerson[]>([])
  const [faces, setFaces] = useState<EnrolledFace[]>([])
  const [loading, setLoading] = useState(true)
  const [enrollDialogOpen, setEnrollDialogOpen] = useState(false)
  const [newEnrollment, setNewEnrollment] = useState({
    name: '',
    role: 'family' as 'owner' | 'family' | 'trusted'
  })
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statusRes, personsRes, facesRes] = await Promise.all([
        securityApi.getStatus(),
        securityApi.listPersons(),
        securityApi.listFaces()
      ])
      setStatus(statusRes.data)
      setPersons(personsRes.data)
      setFaces(facesRes.data)
    } catch (error) {
      console.error('Failed to load security data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleOwnerProtection = async (enabled: boolean) => {
    try {
      await securityApi.toggleOwnerProtection(enabled)
      toast.success(enabled ? 'Owner protection enabled' : 'Owner protection disabled')
      loadData()
    } catch (error) {
      toast.error('Failed to toggle owner protection')
    }
  }

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setSelectedImage(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleEnrollFace = async () => {
    if (!selectedImage) {
      toast.error('Please upload an image')
      return
    }
    try {
      await securityApi.enrollFace({
        name: newEnrollment.name,
        role: newEnrollment.role,
        image: selectedImage
      })
      toast.success('Face enrolled successfully')
      setEnrollDialogOpen(false)
      setNewEnrollment({ name: '', role: 'family' })
      setSelectedImage(null)
      loadData()
    } catch (error) {
      toast.error('Failed to enroll face')
    }
  }

  const handleRemoveFace = async (personId: string) => {
    if (!confirm('Are you sure you want to remove this enrolled face?')) return
    try {
      await securityApi.removeFace(personId)
      toast.success('Face removed')
      loadData()
    } catch (error) {
      toast.error('Failed to remove face')
    }
  }

  const getThreatLevelBadge = (level: string) => {
    switch (level) {
      case 'safe':
        return <Badge className="bg-green-500"><ShieldCheck className="h-3 w-3 mr-1" /> Safe</Badge>
      case 'caution':
        return <Badge className="bg-yellow-500"><Shield className="h-3 w-3 mr-1" /> Caution</Badge>
      case 'alert':
        return <Badge className="bg-orange-500"><ShieldAlert className="h-3 w-3 mr-1" /> Alert</Badge>
      case 'danger':
        return <Badge variant="destructive"><AlertTriangle className="h-3 w-3 mr-1" /> Danger</Badge>
      default:
        return <Badge variant="outline">{level}</Badge>
    }
  }

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'owner':
        return <Badge className="bg-purple-500">Owner</Badge>
      case 'family':
        return <Badge className="bg-blue-500">Family</Badge>
      case 'trusted':
        return <Badge className="bg-green-500">Trusted</Badge>
      default:
        return <Badge variant="outline">{role}</Badge>
    }
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
            <h1 className="text-3xl font-bold">Security Center</h1>
            <p className="text-muted-foreground">
              Monitor threats and manage trusted persons
            </p>
          </div>
          <Dialog open={enrollDialogOpen} onOpenChange={setEnrollDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="h-4 w-4 mr-2" />
                Enroll Face
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Enroll New Face</DialogTitle>
                <DialogDescription>
                  Add a trusted person for facial recognition
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Person Name</Label>
                  <Input
                    id="name"
                    value={newEnrollment.name}
                    onChange={(e) => setNewEnrollment({ ...newEnrollment, name: e.target.value })}
                    placeholder="John Doe"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select
                    value={newEnrollment.role}
                    onValueChange={(value: any) => setNewEnrollment({ ...newEnrollment, role: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="owner">Owner</SelectItem>
                      <SelectItem value="family">Family Member</SelectItem>
                      <SelectItem value="trusted">Trusted Person</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Face Image</Label>
                  <div
                    className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {selectedImage ? (
                      <img
                        src={selectedImage}
                        alt="Preview"
                        className="max-h-48 mx-auto rounded-lg"
                      />
                    ) : (
                      <>
                        <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                          Click to upload a clear face photo
                        </p>
                      </>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleImageUpload}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEnrollDialogOpen(false)}>Cancel</Button>
                <Button onClick={handleEnrollFace}>Enroll Face</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Security Status Cards */}
        <div className="grid gap-6 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Threat Level
              </CardTitle>
            </CardHeader>
            <CardContent>
              {status && getThreatLevelBadge(status.threat_level)}
              <p className="text-sm text-muted-foreground mt-2">
                Anomaly score: {((status?.anomaly_score || 0) * 100).toFixed(1)}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active Trackers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{status?.active_trackers || 0}</div>
              <p className="text-sm text-muted-foreground">Persons being tracked</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Enrolled Faces
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{status?.enrolled_faces || 0}</div>
              <p className="text-sm text-muted-foreground">Trusted persons</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Owner Protection
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-4">
              <Switch
                checked={status?.owner_protection_mode || false}
                onCheckedChange={handleToggleOwnerProtection}
              />
              <span className="text-sm">
                {status?.owner_protection_mode ? 'Enabled' : 'Disabled'}
              </span>
            </CardContent>
          </Card>
        </div>

        {/* Owner Protection Info */}
        {status?.owner_protection_mode && (
          <Card className="border-purple-500 bg-purple-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-purple-500">
                <Home className="h-5 w-5" />
                Owner Protection Mode Active
              </CardTitle>
              <CardDescription>
                The system is actively protecting enrolled owners. Unknown persons will trigger enhanced alerts.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Tracked Persons */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Active Tracking
            </CardTitle>
            <CardDescription>
              Persons currently being tracked across cameras
            </CardDescription>
          </CardHeader>
          <CardContent>
            {persons.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No persons currently being tracked</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Person</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>First Seen</TableHead>
                    <TableHead>Cameras</TableHead>
                    <TableHead>Threat Score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {persons.map((person) => (
                    <TableRow key={person.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4" />
                          <span className="font-medium">
                            {person.name || `Unknown #${person.id.slice(0, 6)}`}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {person.is_known ? (
                          <Badge className="bg-green-500">Known</Badge>
                        ) : (
                          <Badge variant="secondary">Unknown</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {new Date(person.first_seen).toLocaleTimeString()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Camera className="h-3 w-3" />
                          <span>{person.cameras.length}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress 
                            value={person.threat_score * 100} 
                            className="w-16 h-2"
                          />
                          <span className="text-sm">
                            {(person.threat_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Enrolled Faces */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Enrolled Faces
            </CardTitle>
            <CardDescription>
              Trusted persons registered for facial recognition
            </CardDescription>
          </CardHeader>
          <CardContent>
            {faces.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <UserPlus className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No faces enrolled yet</p>
                <Button 
                  variant="outline" 
                  className="mt-4"
                  onClick={() => setEnrollDialogOpen(true)}
                >
                  Enroll First Face
                </Button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {faces.map((face) => (
                  <Card key={face.id} className="border">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                            <User className="h-6 w-6 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="font-medium">{face.name}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {getRoleBadge(face.role)}
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRemoveFace(face.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="mt-4 text-sm text-muted-foreground">
                        <p>Enrolled: {new Date(face.enrolled_at).toLocaleDateString()}</p>
                        {face.last_seen && (
                          <p>Last seen: {new Date(face.last_seen).toLocaleString()}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
