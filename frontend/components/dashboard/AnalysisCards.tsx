"use client";

import { Card } from "@heroui/react";
import { SYSTEM_INSIGHTS } from "@/lib/data";
import { 
  AlertTriangle, ShieldCheck, Activity, Eye, FileText, Settings, LayoutDashboard, MonitorPlay, TrendingUp, TrendingDown, Minus
} from "lucide-react";

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

export function AnalysisCards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {SYSTEM_INSIGHTS.map((insight, idx) => {
        const Icon = iconMap[insight.icon as keyof typeof iconMap] || Activity;
        
        return (
          <Card key={idx} className="border-none bg-background shadow-sm">
            <Card.Content className="p-4 flex flex-row items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-full text-primary">
                <Icon size={24} />
              </div>
              <div className="flex flex-col flex-1">
                <p className="text-sm text-default-500 font-medium">{insight.title}</p>
                <div className="flex items-center gap-2">
                  <h4 className="text-2xl font-bold">{insight.value}</h4>
                  {insight.trend === "up" && <TrendingUp size={16} className="text-danger" />}
                  {insight.trend === "down" && <TrendingDown size={16} className="text-warning" />}
                  {insight.trend === "neutral" && <Minus size={16} className="text-default-400" />}
                </div>
                <p className="text-xs text-default-400 mt-1">{insight.description}</p>
              </div>
            </Card.Content>
          </Card>
        );
      })}
    </div>
  );
}

