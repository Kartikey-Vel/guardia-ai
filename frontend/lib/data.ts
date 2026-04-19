import { AlertTriangle, ShieldCheck, Activity, Eye, FileText, Settings, LayoutDashboard, MonitorPlay } from "lucide-react";

export type SeverityType = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface MockAlert {
  id: string;
  source: string;
  type: string;
  severity: SeverityType;
  timestamp: string;
  description: string;
}

export interface MockCamera {
  id: string;
  name: string;
  status: "active" | "offline";
  lastActivity: string;
  feedUrl: string;
  zone: string;
  riskLevel: number;
}

export interface InsightSummary {
  title: string;
  value: string | number;
  description: string;
  trend?: "up" | "down" | "neutral";
  icon: keyof typeof iconMap;
}

const iconMap = {
  AlertTriangle,
  ShieldCheck,
  Activity,
  Eye,
  FileText,
  Settings,
  LayoutDashboard,
  MonitorPlay,
};

export const MOCK_ALERTS: MockAlert[] = [
  {
    id: "evt-001",
    source: "CAM-01 (Main Entry)",
    type: "Suspicious Loitering",
    severity: "MEDIUM",
    timestamp: "10 min ago",
    description: "Multi-person loitering detected near the main entrance.",
  },
  {
    id: "evt-002",
    source: "CAM-04 (Warehouse A)",
    type: "Unauthorized Access",
    severity: "CRITICAL",
    timestamp: "15 min ago",
    description: "Motion detected in restricted zone during off-hours.",
  },
  {
    id: "evt-003",
    source: "CAM-02 (Lobby)",
    type: "Unattended Object",
    severity: "HIGH",
    timestamp: "1 hour ago",
    description: "Baggage left unattended in the central lobby area.",
  },
  {
    id: "evt-004",
    source: "CAM-05 (Parking Lot)",
    type: "Vehicle Incident",
    severity: "MEDIUM",
    timestamp: "3 hours ago",
    description: "Vehicle parked illegally blocking the emergency exit.",
  },
];

export const MOCK_CAMERAS: MockCamera[] = [
  {
    id: "CAM-01",
    name: "Main Entry",
    status: "active",
    lastActivity: "Live",
    feedUrl: "/cams/cam-placeholder-1.jpg",
    zone: "Entrance",
    riskLevel: 2,
  },
  {
    id: "CAM-02",
    name: "Lobby",
    status: "active",
    lastActivity: "Live",
    feedUrl: "/cams/cam-placeholder-2.jpg",
    zone: "Public",
    riskLevel: 1,
  },
  {
    id: "CAM-03",
    name: "Loading Dock",
    status: "offline",
    lastActivity: "2 mins ago",
    feedUrl: "offline",
    zone: "Logistics",
    riskLevel: 3,
  },
  {
    id: "CAM-04",
    name: "Warehouse A",
    status: "active",
    lastActivity: "Live",
    feedUrl: "/cams/cam-placeholder-3.jpg",
    zone: "Restricted",
    riskLevel: 5,
  },
  {
    id: "CAM-05",
    name: "Parking Lot",
    status: "active",
    lastActivity: "Live",
    feedUrl: "/cams/cam-placeholder-4.jpg",
    zone: "Exterior",
    riskLevel: 4,
  },
];

export const SYSTEM_INSIGHTS: InsightSummary[] = [
  {
    title: "Total Anomalies",
    value: 12,
    description: "Detected in the last 24 hours",
    trend: "up",
    icon: "AlertTriangle",
  },
  {
    title: "System Status",
    value: "Optimal",
    description: "All core services operational",
    icon: "ShieldCheck",
  },
  {
    title: "Active Cameras",
    value: "4 / 5",
    description: "1 camera currently offline",
    trend: "down",
    icon: "MonitorPlay",
  },
  {
    title: "AI Analysis",
    value: "99.8%",
    description: "Confidence rate across events",
    trend: "neutral",
    icon: "Activity",
  },
];
