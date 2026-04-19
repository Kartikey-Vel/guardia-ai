"use client";

import { Card } from "@heroui/react";
import { SYSTEM_INSIGHTS } from "@/lib/data";
import { 
  AlertTriangle, ShieldCheck, Activity, Eye, FileText, Settings, LayoutDashboard, MonitorPlay, TrendingUp, TrendingDown, Minus
} from "lucide-react";
import { motion } from "framer-motion";

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
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-2">
      {SYSTEM_INSIGHTS.map((insight, idx) => {
        const Icon = iconMap[insight.icon as keyof typeof iconMap] || Activity;
        
        return (
          <motion.div 
            key={idx}
            whileHover={{ y: -4, scale: 1.01 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
          >
            <Card className="border border-white/10 dark:border-white/5 bg-background/50 backdrop-blur-md shadow-lg shadow-black/5">
              <Card.Header className="flex flex-row items-center justify-between pb-2">
                <p className="text-sm font-medium text-default-500">{insight.title}</p>
                <div className={`p-2 rounded-xl bg-${idx === 0 ? 'danger' : idx === 1 ? 'success' : idx === 2 ? 'primary' : 'warning'}/10 text-${idx === 0 ? 'danger' : idx === 1 ? 'success' : idx === 2 ? 'primary' : 'warning'} shadow-inner`}>
                  <Icon size={18} />
                </div>
              </Card.Header>
              <Card.Content className="pb-4">
                <div className="flex items-end gap-2">
                  <h4 className="text-3xl font-bold font-outfit tracking-tight">{insight.value}</h4>
                  <div className={`flex items-center text-xs font-medium mb-1 px-1.5 py-0.5 rounded-full ${
                    insight.trend === "up" ? "bg-danger/10 text-danger" : 
                    insight.trend === "down" ? "bg-success/10 text-success" : 
                    "bg-default/10 text-default-500"
                  }`}>
                    {insight.trend === "up" && <TrendingUp size={12} className="mr-1" />}
                    {insight.trend === "down" && <TrendingDown size={12} className="mr-1" />}
                    {insight.trend === "neutral" && <Minus size={12} className="mr-1" />}
                    {insight.trend === "up" ? "+12%" : insight.trend === "down" ? "-4%" : "0%"}
                  </div>
                </div>
                <p className="text-xs text-default-400 mt-2">{insight.description}</p>
              </Card.Content>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}

